"""Bounded two-state toggle-machine learner for Experiment 002."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from model import LearnedModel, TimedResponse, Transaction, learn


TransactionSequence = tuple[Transaction, ...]


@dataclass(frozen=True)
class TwoStateToggleModel:
    control_request: int
    control_response: TimedResponse
    state_models: tuple[LearnedModel, LearnedModel]
    sequence_count: int

    def new_emulator(self) -> "TwoStateEmulator":
        return TwoStateEmulator(self)


class TwoStateEmulator:
    def __init__(self, model: TwoStateToggleModel) -> None:
        self._model = model
        self.state = 0

    def reset(self) -> None:
        self.state = 0

    def emulate(self, request: int) -> TimedResponse | None:
        if request == self._model.control_request:
            response = self._model.control_response
            self.state ^= 1
            return response
        return self._model.state_models[self.state].emulate(request)


@dataclass(frozen=True)
class ToggleLearningResult:
    candidates: tuple[TwoStateToggleModel, ...]

    @property
    def is_complete(self) -> bool:
        return len(self.candidates) == 1

    @property
    def model(self) -> TwoStateToggleModel | None:
        return self.candidates[0] if self.is_complete else None

    @property
    def candidate_requests(self) -> tuple[int, ...]:
        return tuple(candidate.control_request for candidate in self.candidates)


def _timed_response(transaction: Transaction) -> TimedResponse:
    return TimedResponse(transaction.response, transaction.delay_cycles)


def _model_fits(model: LearnedModel, evidence: list[Transaction]) -> bool:
    return all(model.emulate(item.request) == _timed_response(item) for item in evidence)


def _state_is_observable(
    evidence: tuple[list[Transaction], list[Transaction]],
) -> bool:
    by_state: list[dict[int, set[TimedResponse]]] = [{}, {}]
    for state in (0, 1):
        for item in evidence[state]:
            by_state[state].setdefault(item.request, set()).add(_timed_response(item))

    common_requests = set(by_state[0]) & set(by_state[1])
    return any(by_state[0][request] != by_state[1][request] for request in common_requests)


def learn_toggle_machine(
    sequences: Iterable[Iterable[Transaction]],
) -> ToggleLearningResult:
    corpus: tuple[TransactionSequence, ...] = tuple(
        tuple(sequence) for sequence in sequences
    )
    if not corpus or any(not sequence for sequence in corpus):
        raise ValueError("at least one nonempty transaction sequence is required")

    observed_requests = sorted(
        {transaction.request for sequence in corpus for transaction in sequence}
    )
    candidates: list[TwoStateToggleModel] = []

    for control_request in observed_requests:
        state_evidence: tuple[list[Transaction], list[Transaction]] = ([], [])
        control_responses: set[TimedResponse] = set()

        for sequence in corpus:
            state = 0
            for transaction in sequence:
                if transaction.request == control_request:
                    control_responses.add(_timed_response(transaction))
                    state ^= 1
                else:
                    state_evidence[state].append(transaction)

        if len(control_responses) != 1 or not all(state_evidence):
            continue

        state_models = (
            learn(state_evidence[0]),
            learn(state_evidence[1]),
        )
        if not all(model.is_complete for model in state_models):
            continue
        if (
            state_models[0].request_mask != state_models[1].request_mask
            or state_models[0].request_value != state_models[1].request_value
        ):
            continue
        if any(model.accepts(control_request) for model in state_models):
            continue
        if not all(
            _model_fits(state_models[state], state_evidence[state])
            for state in (0, 1)
        ):
            continue
        if not _state_is_observable(state_evidence):
            continue

        candidates.append(
            TwoStateToggleModel(
                control_request=control_request,
                control_response=next(iter(control_responses)),
                state_models=state_models,
                sequence_count=len(corpus),
            )
        )

    return ToggleLearningResult(tuple(candidates))

