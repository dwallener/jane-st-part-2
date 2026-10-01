"""Compact executable protocol program for learned behavioral models.

This is an evidence-backed behavioral IR, not the final pin-level instruction
set. Each guarded transition occupies ten bytes in its canonical encoding.
"""

from __future__ import annotations

from dataclasses import dataclass

from model import BitExpression, ExpressionKind, LearnedModel, TimedResponse
from state_model import TwoStateToggleModel


BYTE_MASK = 0xFF
MAX_STATE = 0x0F
RECORD_BYTES = 10
EXPRESSION_BITS = 5
EXPRESSION_COUNT = 8


def expression_code(expression: BitExpression) -> int:
    """Return the candidate index shared with template_learner RTL."""
    if expression.kind is ExpressionKind.CONSTANT:
        if expression.argument not in (0, 1):
            raise ValueError("constant expression must be zero or one")
        return expression.argument
    if not 0 <= expression.argument < 8:
        raise ValueError("request bit index must be in the range 0..7")
    offset = 0 if expression.kind is ExpressionKind.COPY else 1
    return 2 + 2 * expression.argument + offset


def decode_expression(code: int) -> BitExpression:
    if code in (0, 1):
        return BitExpression(ExpressionKind.CONSTANT, code)
    if not 2 <= code < 18:
        raise ValueError(f"invalid response expression code: {code}")
    kind = ExpressionKind.COPY if code % 2 == 0 else ExpressionKind.INVERT
    return BitExpression(kind, (code - 2) // 2)


@dataclass(frozen=True)
class GuardedTransition:
    state: int
    request_mask: int
    request_value: int
    response_bits: tuple[BitExpression, ...]
    delay_cycles: int
    next_state: int

    def __post_init__(self) -> None:
        if not 0 <= self.state <= MAX_STATE:
            raise ValueError("state must fit in four bits")
        if not 0 <= self.next_state <= MAX_STATE:
            raise ValueError("next_state must fit in four bits")
        if not 0 <= self.request_mask <= BYTE_MASK:
            raise ValueError("request_mask must be an 8-bit value")
        if not 0 <= self.request_value <= BYTE_MASK:
            raise ValueError("request_value must be an 8-bit value")
        if self.request_value & ~self.request_mask:
            raise ValueError("request_value sets bits outside request_mask")
        if len(self.response_bits) != EXPRESSION_COUNT:
            raise ValueError("response template must contain eight expressions")
        if not 0 <= self.delay_cycles <= 0xFFFF:
            raise ValueError("delay must fit in 16 bits")
        for expression in self.response_bits:
            expression_code(expression)

    def accepts(self, request: int) -> bool:
        return (request & self.request_mask) == self.request_value

    def respond(self, request: int) -> TimedResponse:
        value = 0
        for bit, expression in enumerate(self.response_bits):
            value |= expression.evaluate(request) << bit
        return TimedResponse(value, self.delay_cycles)

    def encode(self) -> bytes:
        packed_expressions = 0
        for bit, expression in enumerate(self.response_bits):
            packed_expressions |= expression_code(expression) << (
                bit * EXPRESSION_BITS
            )
        return bytes(
            (
                (self.state << 4) | self.next_state,
                self.request_mask,
                self.request_value,
            )
        ) + packed_expressions.to_bytes(5, "little") + self.delay_cycles.to_bytes(
            2, "little"
        )

    @classmethod
    def decode(cls, record: bytes) -> "GuardedTransition":
        if len(record) != RECORD_BYTES:
            raise ValueError("transition record must contain exactly ten bytes")
        packed_expressions = int.from_bytes(record[3:8], "little")
        response_bits = tuple(
            decode_expression(
                (packed_expressions >> (bit * EXPRESSION_BITS))
                & ((1 << EXPRESSION_BITS) - 1)
            )
            for bit in range(EXPRESSION_COUNT)
        )
        return cls(
            state=record[0] >> 4,
            next_state=record[0] & MAX_STATE,
            request_mask=record[1],
            request_value=record[2],
            response_bits=response_bits,
            delay_cycles=int.from_bytes(record[8:10], "little"),
        )


def _guards_overlap(left: GuardedTransition, right: GuardedTransition) -> bool:
    shared_mask = left.request_mask & right.request_mask
    return ((left.request_value ^ right.request_value) & shared_mask) == 0


@dataclass(frozen=True)
class ProtocolProgram:
    transitions: tuple[GuardedTransition, ...]
    initial_state: int = 0

    def __post_init__(self) -> None:
        if not self.transitions:
            raise ValueError("protocol program must contain at least one transition")
        if not 0 <= self.initial_state <= MAX_STATE:
            raise ValueError("initial_state must fit in four bits")
        states = {transition.state for transition in self.transitions}
        if self.initial_state not in states:
            raise ValueError("initial_state has no outgoing transition")
        for index, left in enumerate(self.transitions):
            for right in self.transitions[index + 1 :]:
                if left.state == right.state and _guards_overlap(left, right):
                    raise ValueError(
                        f"overlapping request guards in state {left.state}"
                    )

    @property
    def encoded_bytes(self) -> int:
        return len(self.transitions) * RECORD_BYTES

    def encode(self) -> bytes:
        return b"".join(transition.encode() for transition in self.transitions)

    @classmethod
    def decode(cls, data: bytes, initial_state: int = 0) -> "ProtocolProgram":
        if not data or len(data) % RECORD_BYTES:
            raise ValueError("program length must be a nonzero multiple of ten")
        transitions = tuple(
            GuardedTransition.decode(data[offset : offset + RECORD_BYTES])
            for offset in range(0, len(data), RECORD_BYTES)
        )
        return cls(transitions, initial_state)

    def new_emulator(self) -> "ProtocolProgramEmulator":
        return ProtocolProgramEmulator(self)


class ProtocolProgramEmulator:
    def __init__(self, program: ProtocolProgram) -> None:
        self._program = program
        self.state = program.initial_state

    def reset(self) -> None:
        self.state = self._program.initial_state

    def emulate(self, request: int) -> TimedResponse | None:
        if not 0 <= request <= BYTE_MASK:
            raise ValueError("request must be an 8-bit value")
        matches = tuple(
            transition
            for transition in self._program.transitions
            if transition.state == self.state and transition.accepts(request)
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise RuntimeError("validated program produced an ambiguous match")
        transition = matches[0]
        response = transition.respond(request)
        self.state = transition.next_state
        return response


def _constant_template(value: int) -> tuple[BitExpression, ...]:
    return tuple(
        BitExpression(ExpressionKind.CONSTANT, (value >> bit) & 1)
        for bit in range(8)
    )


def _transition_from_model(
    model: LearnedModel, state: int, next_state: int
) -> GuardedTransition:
    if not model.is_complete or model.delay_cycles is None:
        raise ValueError("cannot compile an incomplete learned model")
    response_bits = tuple(model.response_bits)
    if any(expression is None for expression in response_bits):
        raise ValueError("cannot compile an ambiguous response template")
    return GuardedTransition(
        state=state,
        request_mask=model.request_mask,
        request_value=model.request_value,
        response_bits=response_bits,  # type: ignore[arg-type]
        delay_cycles=model.delay_cycles,
        next_state=next_state,
    )


def compile_stateless(model: LearnedModel) -> ProtocolProgram:
    return ProtocolProgram((_transition_from_model(model, 0, 0),))


def compile_toggle(model: TwoStateToggleModel) -> ProtocolProgram:
    control_template = _constant_template(model.control_response.value)
    transitions: list[GuardedTransition] = []
    for state in (0, 1):
        transitions.append(
            GuardedTransition(
                state=state,
                request_mask=0xFF,
                request_value=model.control_request,
                response_bits=control_template,
                delay_cycles=model.control_response.delay_cycles,
                next_state=state ^ 1,
            )
        )
        transitions.append(_transition_from_model(model.state_models[state], state, state))
    return ProtocolProgram(tuple(transitions))
