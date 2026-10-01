"""Invented protocols designed to break shallow replay or overconfident inference."""

from __future__ import annotations

from dataclasses import dataclass

from edge_trace import Trace
from framing_hypothesis import FramingHypothesis, PinRoles
from integrity_hypothesis import CRC8_CATALOG, frame_with_integrity, infer_integrity, validate_frame
from model import BitExpression, ExpressionKind, Transaction
from protocol_program import GuardedTransition, ProtocolProgram
from spi_causality import CausalityClass, analyze_spi_causality
from state_model import learn_toggle_machine
from stateful_peripheral import training_sequences
from variant_link import BitOrder, SamplingEdge, encode_variant
from variable_framing import FramingKind, learn_variable_framing
from width_hypothesis import infer_width


@dataclass(frozen=True)
class AdversarialResult:
    name: str
    dimensions: tuple[str, ...]
    observations_required: int
    surviving_equivalence: int
    passed: bool
    outcome: str
    refusal: str | None


def run_adversarial_corpus() -> tuple[AdversarialResult, ...]:
    results: list[AdversarialResult] = []

    hypothesis = FramingHypothesis(SamplingEdge.RISING, BitOrder.MSB_FIRST)
    six = tuple(
        encode_variant(Transaction(value, value ^ 0x15, 4), SamplingEdge.RISING,
                       BitOrder.MSB_FIRST, frame_width=6)
        for value in (0, 3, 12, 42)
    )
    width = infer_width(six, hypothesis, PinRoles())
    results.append(AdversarialResult(
        "six_bit_not_byte", ("variable_width",), 4, len(width.symbol_widths),
        width.phase_shape.request_bits == 6 and 6 in width.symbol_widths,
        f"observed 6-bit phases; compatible granularities={width.symbol_widths}", None))

    ambiguous_frames = ((0x02, 0x41, 0x7E), (0x03, 0x42, 0x43, 0x7E))
    framing = learn_variable_framing(ambiguous_frames)
    results.append(AdversarialResult(
        "length_or_delimiter", ("length_framing", "delimiter_framing", "ambiguity"), 2, len(framing.candidates),
        set(framing.kinds) == {FramingKind.LENGTH, FramingKind.DELIMITER},
        "retained both consistent frame grammars", "requires one distinguishing frame"))

    crc = CRC8_CATALOG[0]
    frames = tuple(frame_with_integrity(payload, crc) for payload in ((1, 2), (0x10, 0x20), (0xDE, 0xAD)))
    integrity = infer_integrity(frames)
    corrupt = (frames[-1][0] ^ 1,) + frames[-1][1:]
    results.append(AdversarialResult(
        "crc_with_corruption", ("integrity", "corrupted_trace"), len(frames), len(integrity.candidates),
        integrity.is_complete and integrity.model == crc and not validate_frame(corrupt, crc),
        "identified CRC-8/SMBUS and rejected held-out corruption", "corrupt frame refused"))

    state = learn_toggle_machine(training_sequences())
    results.append(AdversarialResult(
        "history_changes_answer", ("state",), len(training_sequences()), len(state.candidates), state.is_complete,
        "same request has distinct responses across inferred toggle state",
        None if state.is_complete else "state evidence remains ambiguous"))

    expressions = [BitExpression(ExpressionKind.CONSTANT, 0) for _ in range(8)]
    expressions[7] = BitExpression(ExpressionKind.COPY, 0)
    program = ProtocolProgram((GuardedTransition(0, 0, 0, tuple(expressions), 0, 0),))
    causality = analyze_spi_causality(program)
    results.append(AdversarialResult(
        "future_bit_dependency", ("causally_impossible",), 1, 0,
        causality.classification is CausalityClass.NONCAUSAL,
        "detected response bit 7 dependency on future request bit 0",
        "same-frame electrical execution refused"))

    # A variable-width corpus must not be averaged into a fictional fixed width.
    eight = encode_variant(Transaction(0xAA, 0x55, 4), SamplingEdge.RISING,
                           BitOrder.MSB_FIRST, frame_width=8)
    rejected = False
    try:
        infer_width((six[0], eight), hypothesis, PinRoles())
    except ValueError:
        rejected = True
    results.append(AdversarialResult(
        "mixed_width_contradiction", ("variable_width", "corrupted_trace"), 2, 0, rejected,
        "rejected incompatible fixed-width evidence",
        "corpus has variable framed phase widths" if rejected else None))
    return tuple(results)
