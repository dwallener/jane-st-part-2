"""Bounded search for serial-link pin roles and framing conventions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

from edge_trace import Trace
from framing_hypothesis import (
    FramingCandidate,
    FramingHypothesis,
    PinRoles,
    decode_with_roles,
)
from model import learn
from variant_link import BitOrder, SamplingEdge


@dataclass(frozen=True)
class RoleCandidate:
    roles: PinRoles
    framing: FramingCandidate


@dataclass(frozen=True)
class RoleInference:
    candidates: tuple[RoleCandidate, ...]
    hypothesis_count: int

    @property
    def role_assignments(self) -> tuple[PinRoles, ...]:
        return tuple(dict.fromkeys(candidate.roles for candidate in self.candidates))

    @property
    def sampling_edges(self) -> tuple[SamplingEdge, ...]:
        return tuple(
            dict.fromkeys(
                candidate.framing.hypothesis.sampling_edge
                for candidate in self.candidates
            )
        )

    @property
    def bit_orders(self) -> tuple[BitOrder, ...]:
        return tuple(
            dict.fromkeys(
                candidate.framing.hypothesis.bit_order
                for candidate in self.candidates
            )
        )


def infer_pin_roles(
    traces: tuple[Trace, ...],
    *,
    input_pins: tuple[int, ...] = (0x01, 0x02, 0x04),
    output_pins: tuple[int, ...] = (0x01, 0x02),
) -> RoleInference:
    if not traces:
        raise ValueError("at least one trace is required")
    if len(input_pins) != 3 or len(set(input_pins)) != 3:
        raise ValueError("exactly three distinct input pins are required")
    if len(output_pins) != 2 or len(set(output_pins)) != 2:
        raise ValueError("exactly two distinct output pins are required")

    candidates: list[RoleCandidate] = []
    hypothesis_count = 0
    for clock, request_data, select in permutations(input_pins):
        for response_data, response_valid in permutations(output_pins):
            roles = PinRoles(
                clock=clock,
                request_data=request_data,
                select=select,
                response_data=response_data,
                response_valid=response_valid,
            )
            for sampling_edge in SamplingEdge:
                for bit_order in BitOrder:
                    hypothesis_count += 1
                    hypothesis = FramingHypothesis(sampling_edge, bit_order)
                    try:
                        transactions = tuple(
                            decode_with_roles(trace, hypothesis, roles)
                            for trace in traces
                        )
                        model = learn(transactions)
                        if not model.is_complete or model.request_mask == 0xFF:
                            continue
                    except ValueError:
                        continue
                    candidates.append(
                        RoleCandidate(
                            roles,
                            FramingCandidate(hypothesis, transactions, model),
                        )
                    )
    return RoleInference(tuple(candidates), hypothesis_count)
