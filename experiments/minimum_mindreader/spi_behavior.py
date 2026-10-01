"""Joint SPI physical and behavioral inference across repeated transfers."""

from __future__ import annotations

from dataclasses import dataclass

from known_protocol_corpus import BenchmarkCase, make_spi_case
from model import LearnedModel, TimedResponse, Transaction, learn
from protocol_program import ProtocolProgram, compile_stateless
from spi_hypothesis import SpiBitOrder, SpiCandidate, SpiHypothesis, infer_spi


TRAINING_REQUESTS = (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA8, 0xAF)
HELD_OUT_REQUEST = 0xA7


def lossy_response(request: int) -> int:
    return 0x60 | (request & 0x03)


def reversible_response(request: int) -> int:
    return 0x60 | (request & 0x0F)


def make_spi_behavior_corpus(
    mode: int,
    msb_first: bool,
    *,
    response_function=lossy_response,
) -> tuple[BenchmarkCase, ...]:
    return tuple(
        make_spi_case(
            mode,
            msb_first,
            request=request,
            response=response_function(request),
        )
        for request in TRAINING_REQUESTS
    )


@dataclass(frozen=True)
class SpiBehaviorCandidate:
    hypothesis: SpiHypothesis
    model: LearnedModel

    def compile(self) -> ProtocolProgram:
        return compile_stateless(self.model)


@dataclass(frozen=True)
class SpiBehaviorInference:
    candidates: tuple[SpiBehaviorCandidate, ...]
    waveform_count: int
    physical_hypotheses_per_waveform: int

    @property
    def request_pins(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.data_a_pin for item in self.candidates)
        )

    @property
    def response_pins(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.data_b_pin for item in self.candidates)
        )

    @property
    def bit_orders(self) -> tuple[SpiBitOrder, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.bit_order for item in self.candidates)
        )


def _candidate_maps(
    cases: tuple[BenchmarkCase, ...],
) -> tuple[tuple[SpiCandidate, ...], tuple[dict[SpiHypothesis, SpiCandidate], ...]]:
    inferences = tuple(infer_spi(case.inference_input()) for case in cases)
    first_candidates = inferences[0].candidates
    maps = tuple(
        {candidate.hypothesis: candidate for candidate in inference.candidates}
        for inference in inferences
    )
    return first_candidates, maps


def infer_spi_behavior(cases: tuple[BenchmarkCase, ...]) -> SpiBehaviorInference:
    if not cases:
        raise ValueError("at least one SPI transfer is required")
    if any(case.waveform.pin_count != 4 for case in cases):
        raise ValueError("all SPI transfers must contain exactly four pins")

    first_candidates, candidate_maps = _candidate_maps(cases)
    survivors: list[SpiBehaviorCandidate] = []
    for first in first_candidates:
        hypothesis = first.hypothesis
        if not all(hypothesis in mapping for mapping in candidate_maps):
            continue
        transactions = tuple(
            Transaction(
                request=mapping[hypothesis].data_a_word,
                response=mapping[hypothesis].data_b_word,
                delay_cycles=0,
            )
            for mapping in candidate_maps
        )
        model = learn(transactions)
        if model.is_complete and model.request_mask != 0xFF:
            survivors.append(SpiBehaviorCandidate(hypothesis, model))

    return SpiBehaviorInference(
        candidates=tuple(survivors),
        waveform_count=len(cases),
        physical_hypotheses_per_waveform=384,
    )


def emulate_held_out(candidate: SpiBehaviorCandidate, request: int) -> TimedResponse | None:
    return candidate.compile().new_emulator().emulate(request)
