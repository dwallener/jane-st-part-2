"""Place request-family decisions and response emissions on SPI wire time."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from model import ExpressionKind
from protocol_program import GuardedTransition, ProtocolProgram
from spi_hypothesis import SpiBitOrder


class GuardRisk(Enum):
    GUARD_FREE = "guard_free"
    SPECULATIVE_CONSTANT_PREFIX = "speculative_constant_prefix"
    SPECULATIVE_DEPENDENT_OUTPUT = "speculative_dependent_output"


@dataclass(frozen=True)
class TransitionGuardAnalysis:
    transition_index: int
    decision_time: int | None
    speculative_response_bits: tuple[int, ...]
    speculative_dependent_bits: tuple[int, ...]
    risk: GuardRisk


def _time(bit: int, order: SpiBitOrder) -> int:
    return 7 - bit if order is SpiBitOrder.MSB_FIRST else bit


def analyze_transition_guard(
    transition: GuardedTransition,
    transition_index: int = 0,
    *,
    bit_order: SpiBitOrder = SpiBitOrder.MSB_FIRST,
) -> TransitionGuardAnalysis:
    guarded_bits = tuple(bit for bit in range(8) if transition.request_mask >> bit & 1)
    if not guarded_bits:
        return TransitionGuardAnalysis(
            transition_index, None, (), (), GuardRisk.GUARD_FREE
        )
    decision_time = max(_time(bit, bit_order) for bit in guarded_bits)
    speculative = tuple(
        bit for bit in range(8) if _time(bit, bit_order) <= decision_time
    )
    dependent = tuple(
        bit
        for bit in speculative
        if transition.response_bits[bit].kind is not ExpressionKind.CONSTANT
    )
    risk = (
        GuardRisk.SPECULATIVE_DEPENDENT_OUTPUT
        if dependent
        else GuardRisk.SPECULATIVE_CONSTANT_PREFIX
    )
    return TransitionGuardAnalysis(
        transition_index,
        decision_time,
        speculative,
        dependent,
        risk,
    )


def analyze_program_guards(
    program: ProtocolProgram,
    *,
    bit_order: SpiBitOrder = SpiBitOrder.MSB_FIRST,
) -> tuple[TransitionGuardAnalysis, ...]:
    return tuple(
        analyze_transition_guard(transition, index, bit_order=bit_order)
        for index, transition in enumerate(program.transitions)
    )
