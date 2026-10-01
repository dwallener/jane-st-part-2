"""Infer framed phase widths while preserving symbol-granularity ambiguity."""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from edge_trace import Trace
from framing_hypothesis import FramingHypothesis, PinRoles
from variant_link import SamplingEdge


@dataclass(frozen=True)
class PhaseShape:
    request_bits: int
    response_bits: int


@dataclass(frozen=True)
class WidthInference:
    phase_shape: PhaseShape
    symbol_widths: tuple[int, ...]

    def symbols_per_request(self, symbol_width: int) -> int:
        if symbol_width not in self.symbol_widths:
            raise ValueError("symbol width is not compatible with this phase shape")
        return self.phase_shape.request_bits // symbol_width

    def symbols_per_response(self, symbol_width: int) -> int:
        if symbol_width not in self.symbol_widths:
            raise ValueError("symbol width is not compatible with this phase shape")
        return self.phase_shape.response_bits // symbol_width


def observe_phase_shape(
    trace: Trace, hypothesis: FramingHypothesis, roles: PinRoles
) -> PhaseShape:
    if any(event.marker is not None for event in trace.events):
        raise ValueError("width inference requires markerless traces")

    previous_input = 0
    previous_output = 0
    request_bits = 0
    response_bits = 0
    saw_select = False
    saw_valid = False

    for event in trace.events:
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
        valid_rising = not (previous_output & roles.response_valid) and bool(
            event.output_value & roles.response_valid
        )

        if select_rising:
            if saw_select:
                raise ValueError("multiple select assertions")
            saw_select = True
        if valid_rising:
            if saw_valid:
                raise ValueError("multiple response-valid assertions")
            saw_valid = True

        if sample_edge and event.input_value & roles.select:
            if event.output_value & roles.response_valid:
                if event.output_changed & roles.response_data:
                    raise ValueError("response data changes on candidate sampling edge")
                response_bits += 1
            else:
                if event.input_changed & roles.request_data:
                    raise ValueError("request data changes on candidate sampling edge")
                request_bits += 1

        previous_input = event.input_value
        previous_output = event.output_value

    if not saw_select or not saw_valid:
        raise ValueError("trace lacks complete select and response-valid phases")
    if previous_input != 0 or previous_output != 0:
        raise ValueError("trace did not return to idle")
    if request_bits == 0 or response_bits == 0:
        raise ValueError("both phases must contain sampled bits")
    return PhaseShape(request_bits, response_bits)


def infer_width(
    traces: tuple[Trace, ...],
    hypothesis: FramingHypothesis,
    roles: PinRoles,
    *,
    maximum_symbol_width: int = 16,
) -> WidthInference:
    if not traces:
        raise ValueError("at least one trace is required")
    if maximum_symbol_width < 1:
        raise ValueError("maximum_symbol_width must be positive")

    shapes = tuple(observe_phase_shape(trace, hypothesis, roles) for trace in traces)
    if len(set(shapes)) != 1:
        raise ValueError("corpus has variable framed phase widths")
    shape = shapes[0]
    common_width = gcd(shape.request_bits, shape.response_bits)
    symbol_widths = tuple(
        width
        for width in range(1, min(common_width, maximum_symbol_width) + 1)
        if shape.request_bits % width == 0 and shape.response_bits % width == 0
    )
    return WidthInference(shape, symbol_widths)
