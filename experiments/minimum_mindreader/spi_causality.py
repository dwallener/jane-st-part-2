"""Determine whether a learned word relation can execute during one SPI frame."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from model import ExpressionKind
from protocol_program import ProtocolProgram
from spi_hypothesis import SpiBitOrder, SpiSamplingEdge


class CausalityClass(Enum):
    PRECOMPUTABLE = "precomputable"
    PREFIX_CAUSAL = "prefix_causal"
    SAME_SYMBOL_CAUSAL = "same_symbol_causal"
    NONCAUSAL = "noncausal"


class TimingRequirement(Enum):
    LAUNCH_TO_SAMPLE = "measure_launch_to_sample_margin"
    SELECT_TO_FIRST_SAMPLE = "measure_select_to_first_sample_margin"
    FUTURE_REQUEST_BIT = "requires_future_request_bit"


@dataclass(frozen=True)
class BitDependency:
    transition_index: int
    response_bit: int
    response_time: int
    request_bit: int
    request_time: int

    @property
    def offset(self) -> int:
        """Positive means the request bit is available earlier."""
        return self.response_time - self.request_time


@dataclass(frozen=True)
class SpiCausalityAnalysis:
    classification: CausalityClass
    dependencies: tuple[BitDependency, ...]
    timing_requirements: tuple[TimingRequirement, ...]

    @property
    def executable_in_one_frame(self) -> bool:
        return self.classification is not CausalityClass.NONCAUSAL


def _temporal_position(bit: int, bit_order: SpiBitOrder) -> int:
    return 7 - bit if bit_order is SpiBitOrder.MSB_FIRST else bit


def analyze_spi_causality(
    program: ProtocolProgram,
    *,
    bit_order: SpiBitOrder = SpiBitOrder.MSB_FIRST,
    sampling_edge: SpiSamplingEdge = SpiSamplingEdge.LEADING,
) -> SpiCausalityAnalysis:
    dependencies: list[BitDependency] = []
    for transition_index, transition in enumerate(program.transitions):
        for response_bit, expression in enumerate(transition.response_bits):
            if expression.kind is ExpressionKind.CONSTANT:
                continue
            dependencies.append(
                BitDependency(
                    transition_index=transition_index,
                    response_bit=response_bit,
                    response_time=_temporal_position(response_bit, bit_order),
                    request_bit=expression.argument,
                    request_time=_temporal_position(expression.argument, bit_order),
                )
            )

    if not dependencies:
        return SpiCausalityAnalysis(CausalityClass.PRECOMPUTABLE, (), ())

    if any(dependency.offset < 0 for dependency in dependencies):
        return SpiCausalityAnalysis(
            CausalityClass.NONCAUSAL,
            tuple(dependencies),
            (TimingRequirement.FUTURE_REQUEST_BIT,),
        )

    same_symbol = tuple(
        dependency for dependency in dependencies if dependency.offset == 0
    )
    if not same_symbol:
        return SpiCausalityAnalysis(
            CausalityClass.PREFIX_CAUSAL, tuple(dependencies), ()
        )

    requirements = [TimingRequirement.LAUNCH_TO_SAMPLE]
    if sampling_edge is SpiSamplingEdge.LEADING and any(
        dependency.response_time == 0 for dependency in same_symbol
    ):
        requirements.insert(0, TimingRequirement.SELECT_TO_FIRST_SAMPLE)
    return SpiCausalityAnalysis(
        CausalityClass.SAME_SYMBOL_CAUSAL,
        tuple(dependencies),
        tuple(requirements),
    )
