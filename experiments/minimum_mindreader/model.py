"""Bounded transaction learner for CLAIM-000 Experiment 000."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


BYTE_WIDTH = 8
BYTE_MASK = (1 << BYTE_WIDTH) - 1


@dataclass(frozen=True)
class Transaction:
    request: int
    response: int
    delay_cycles: int

    def __post_init__(self) -> None:
        if not 0 <= self.request <= BYTE_MASK:
            raise ValueError("request must be an 8-bit value")
        if not 0 <= self.response <= BYTE_MASK:
            raise ValueError("response must be an 8-bit value")
        if self.delay_cycles < 0:
            raise ValueError("delay_cycles must be non-negative")


@dataclass(frozen=True)
class TimedResponse:
    value: int
    delay_cycles: int


class ExpressionKind(Enum):
    CONSTANT = "constant"
    COPY = "copy"
    INVERT = "invert"


@dataclass(frozen=True)
class BitExpression:
    kind: ExpressionKind
    argument: int

    def evaluate(self, request: int) -> int:
        if self.kind is ExpressionKind.CONSTANT:
            return self.argument

        source = (request >> self.argument) & 1
        if self.kind is ExpressionKind.COPY:
            return source
        return source ^ 1

    def describe(self) -> str:
        if self.kind is ExpressionKind.CONSTANT:
            return str(self.argument)
        operation = "request" if self.kind is ExpressionKind.COPY else "~request"
        return f"{operation}[{self.argument}]"


@dataclass(frozen=True)
class LearnedModel:
    request_mask: int
    request_value: int
    response_bits: tuple[BitExpression | None, ...]
    response_candidates: tuple[tuple[BitExpression, ...], ...]
    delay_cycles: int | None
    evidence_count: int

    @property
    def is_complete(self) -> bool:
        return self.delay_cycles is not None and all(
            expression is not None for expression in self.response_bits
        )

    def accepts(self, request: int) -> bool:
        return (request & self.request_mask) == self.request_value

    def emulate(self, request: int) -> TimedResponse | None:
        if not 0 <= request <= BYTE_MASK:
            raise ValueError("request must be an 8-bit value")
        if not self.is_complete or not self.accepts(request):
            return None

        response = 0
        for bit, expression in enumerate(self.response_bits):
            assert expression is not None
            response |= expression.evaluate(request) << bit

        assert self.delay_cycles is not None
        return TimedResponse(response, self.delay_cycles)

    def describe(self) -> dict[str, object]:
        return {
            "request_mask": f"0x{self.request_mask:02X}",
            "request_value": f"0x{self.request_value:02X}",
            "response_bits_lsb_first": [
                expression.describe() if expression is not None else "AMBIGUOUS"
                for expression in self.response_bits
            ],
            "delay_cycles": self.delay_cycles,
            "evidence_count": self.evidence_count,
            "complete": self.is_complete,
        }


def _stable_request_predicate(
    examples: tuple[Transaction, ...],
) -> tuple[int, int]:
    mask = 0
    value = 0
    for bit in range(BYTE_WIDTH):
        observed = {(example.request >> bit) & 1 for example in examples}
        if len(observed) == 1:
            mask |= 1 << bit
            value |= next(iter(observed)) << bit
    return mask, value


def _candidate_expressions(variable_bits: tuple[int, ...]) -> tuple[BitExpression, ...]:
    candidates = [
        BitExpression(ExpressionKind.CONSTANT, 0),
        BitExpression(ExpressionKind.CONSTANT, 1),
    ]
    for bit in variable_bits:
        candidates.append(BitExpression(ExpressionKind.COPY, bit))
        candidates.append(BitExpression(ExpressionKind.INVERT, bit))
    return tuple(candidates)


def learn(examples: Iterable[Transaction]) -> LearnedModel:
    evidence = tuple(examples)
    if not evidence:
        raise ValueError("at least one transaction is required")

    request_mask, request_value = _stable_request_predicate(evidence)
    variable_bits = tuple(
        bit for bit in range(BYTE_WIDTH) if not (request_mask & (1 << bit))
    )
    expressions = _candidate_expressions(variable_bits)

    selected: list[BitExpression | None] = []
    all_candidates: list[tuple[BitExpression, ...]] = []
    for response_bit in range(BYTE_WIDTH):
        matches = tuple(
            expression
            for expression in expressions
            if all(
                expression.evaluate(example.request)
                == ((example.response >> response_bit) & 1)
                for example in evidence
            )
        )
        all_candidates.append(matches)
        selected.append(matches[0] if len(matches) == 1 else None)

    delays = {example.delay_cycles for example in evidence}
    delay_cycles = next(iter(delays)) if len(delays) == 1 else None

    return LearnedModel(
        request_mask=request_mask,
        request_value=request_value,
        response_bits=tuple(selected),
        response_candidates=tuple(all_candidates),
        delay_cycles=delay_cycles,
        evidence_count=len(evidence),
    )


class ReplayBaseline:
    """Exact request-indexed replay, used as the negative control."""

    def __init__(self, examples: Iterable[Transaction]) -> None:
        self._responses: dict[int, TimedResponse] = {}
        for example in examples:
            response = TimedResponse(example.response, example.delay_cycles)
            previous = self._responses.get(example.request)
            if previous is not None and previous != response:
                raise ValueError("conflicting replay examples for one request")
            self._responses[example.request] = response

    def emulate(self, request: int) -> TimedResponse | None:
        return self._responses.get(request)

