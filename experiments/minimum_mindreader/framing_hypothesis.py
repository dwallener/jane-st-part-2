"""Bounded framing search over sampling edge and bit order."""

from __future__ import annotations

from dataclasses import dataclass

from edge_trace import Trace
from model import LearnedModel, Transaction, learn
from synthetic_link import (
    BYTE_BITS,
    CLOCK,
    REQUEST_DATA,
    RESPONSE_DATA,
    RESPONSE_VALID,
    SELECT,
)
from variant_link import BitOrder, SamplingEdge


@dataclass(frozen=True)
class FramingHypothesis:
    sampling_edge: SamplingEdge
    bit_order: BitOrder


@dataclass(frozen=True)
class PinRoles:
    clock: int = CLOCK
    request_data: int = REQUEST_DATA
    select: int = SELECT
    response_data: int = RESPONSE_DATA
    response_valid: int = RESPONSE_VALID


@dataclass(frozen=True)
class FramingCandidate:
    hypothesis: FramingHypothesis
    transactions: tuple[Transaction, ...]
    model: LearnedModel


@dataclass(frozen=True)
class FramingInference:
    candidates: tuple[FramingCandidate, ...]
    rejected: tuple[tuple[FramingHypothesis, str], ...]

    @property
    def sampling_edges(self) -> tuple[SamplingEdge, ...]:
        return tuple(
            dict.fromkeys(candidate.hypothesis.sampling_edge for candidate in self.candidates)
        )

    @property
    def bit_orders(self) -> tuple[BitOrder, ...]:
        return tuple(
            dict.fromkeys(candidate.hypothesis.bit_order for candidate in self.candidates)
        )


def _bits_to_byte(bits: list[int], bit_order: BitOrder, phase: str) -> int:
    if len(bits) != BYTE_BITS:
        raise ValueError(f"{phase} contains {len(bits)} sampled bits; expected 8")
    if bit_order is BitOrder.MSB_FIRST:
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return value
    return sum(bit << index for index, bit in enumerate(bits))


def decode_with_hypothesis(
    trace: Trace, hypothesis: FramingHypothesis
) -> Transaction:
    return decode_with_roles(trace, hypothesis, PinRoles())


def decode_with_roles(
    trace: Trace, hypothesis: FramingHypothesis, roles: PinRoles
) -> Transaction:
    if any(event.marker is not None for event in trace.events):
        raise ValueError("framing inference requires markerless traces")

    request_bits: list[int] = []
    response_bits: list[int] = []
    previous_input = 0
    previous_output = 0
    cycle = 0
    request_end_cycle: int | None = None
    response_start_cycle: int | None = None
    saw_select = False

    for event in trace.events:
        cycle += event.delta_cycles
        clock_rising = not (previous_input & roles.clock) and bool(
            event.input_value & roles.clock
        )
        clock_falling = bool(previous_input & roles.clock) and not (
            event.input_value & roles.clock
        )
        sample_edge = (
            clock_rising
            if hypothesis.sampling_edge is SamplingEdge.RISING
            else clock_falling
        )
        select_rising = not (previous_input & roles.select) and bool(
            event.input_value & roles.select
        )
        select_falling = bool(previous_input & roles.select) and not (
            event.input_value & roles.select
        )
        valid_rising = not (previous_output & roles.response_valid) and bool(
            event.output_value & roles.response_valid
        )

        if select_rising:
            if saw_select:
                raise ValueError("multiple select assertions")
            saw_select = True
        if valid_rising:
            response_start_cycle = cycle

        if sample_edge and event.input_value & roles.select:
            if event.output_value & roles.response_valid:
                if event.output_changed & roles.response_data:
                    raise ValueError("response data changes on candidate sampling edge")
                response_bits.append(int(bool(event.output_value & roles.response_data)))
            else:
                if event.input_changed & roles.request_data:
                    raise ValueError("request data changes on candidate sampling edge")
                request_bits.append(int(bool(event.input_value & roles.request_data)))

        if clock_falling and len(request_bits) == BYTE_BITS and request_end_cycle is None:
            request_end_cycle = cycle
        if select_falling and event.output_value & roles.response_valid:
            raise ValueError("select ended while response-valid remained asserted")

        previous_input = event.input_value
        previous_output = event.output_value

    if not saw_select or previous_input != 0 or previous_output != 0:
        raise ValueError("trace does not contain one complete selected transaction")
    if request_end_cycle is None or response_start_cycle is None:
        raise ValueError("transaction timing is incomplete")
    if response_start_cycle < request_end_cycle:
        raise ValueError("response began before request completion")

    return Transaction(
        request=_bits_to_byte(request_bits, hypothesis.bit_order, "request"),
        response=_bits_to_byte(response_bits, hypothesis.bit_order, "response"),
        delay_cycles=response_start_cycle - request_end_cycle,
    )


def infer_framing(traces: tuple[Trace, ...]) -> FramingInference:
    if not traces:
        raise ValueError("at least one trace is required")

    candidates: list[FramingCandidate] = []
    rejected: list[tuple[FramingHypothesis, str]] = []
    for sampling_edge in SamplingEdge:
        for bit_order in BitOrder:
            hypothesis = FramingHypothesis(sampling_edge, bit_order)
            try:
                transactions = tuple(
                    decode_with_hypothesis(trace, hypothesis) for trace in traces
                )
                model = learn(transactions)
                if not model.is_complete:
                    raise ValueError("decoded corpus does not determine a complete model")
                candidates.append(FramingCandidate(hypothesis, transactions, model))
            except ValueError as error:
                rejected.append((hypothesis, str(error)))
    return FramingInference(tuple(candidates), tuple(rejected))
