"""Bounded active disambiguation for Experiment 003."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

from model import LearnedModel, TimedResponse, Transaction, learn


DEFAULT_MAX_CANDIDATES = 4096


@dataclass(frozen=True)
class ProbeSuggestion:
    request: int
    distinct_outcomes: int
    worst_case_remaining: int


@dataclass(frozen=True)
class HypothesisSet:
    candidates: tuple[LearnedModel, ...]
    observed_requests: frozenset[int]

    @property
    def is_resolved(self) -> bool:
        return len(self.candidates) == 1

    @property
    def is_contradictory(self) -> bool:
        return not self.candidates

    @property
    def resolved_model(self) -> LearnedModel | None:
        return self.candidates[0] if self.is_resolved else None

    def suggest_probe(
        self,
        allowed_requests: Iterable[int] = range(256),
    ) -> ProbeSuggestion | None:
        if len(self.candidates) < 2:
            return None

        suggestions: list[ProbeSuggestion] = []
        for request in allowed_requests:
            if request in self.observed_requests:
                continue
            predictions = [candidate.emulate(request) for candidate in self.candidates]
            if any(prediction is None for prediction in predictions):
                continue

            partitions: dict[TimedResponse, int] = {}
            for prediction in predictions:
                assert prediction is not None
                partitions[prediction] = partitions.get(prediction, 0) + 1
            if len(partitions) < 2:
                continue
            suggestions.append(
                ProbeSuggestion(
                    request=request,
                    distinct_outcomes=len(partitions),
                    worst_case_remaining=max(partitions.values()),
                )
            )

        if not suggestions:
            return None
        return min(
            suggestions,
            key=lambda item: (
                item.worst_case_remaining,
                -item.distinct_outcomes,
                item.request,
            ),
        )

    def observe(self, request: int, response: TimedResponse) -> "HypothesisSet":
        survivors = tuple(
            candidate
            for candidate in self.candidates
            if candidate.emulate(request) == response
        )
        return HypothesisSet(
            candidates=survivors,
            observed_requests=self.observed_requests | {request},
        )


def expand_hypotheses(
    examples: Iterable[Transaction],
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> HypothesisSet:
    evidence = tuple(examples)
    partial = learn(evidence)
    if partial.delay_cycles is None:
        raise ValueError("response timing is ambiguous")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")

    candidate_count = 1
    for expressions in partial.response_candidates:
        candidate_count *= len(expressions)
        if candidate_count > max_candidates:
            raise ValueError(
                f"candidate space contains more than {max_candidates} models"
            )
    if candidate_count == 0:
        return HypothesisSet((), frozenset(item.request for item in evidence))

    candidates: list[LearnedModel] = []
    for response_bits in product(*partial.response_candidates):
        candidates.append(
            LearnedModel(
                request_mask=partial.request_mask,
                request_value=partial.request_value,
                response_bits=tuple(response_bits),
                response_candidates=tuple((expression,) for expression in response_bits),
                delay_cycles=partial.delay_cycles,
                evidence_count=partial.evidence_count,
            )
        )

    return HypothesisSet(
        candidates=tuple(candidates),
        observed_requests=frozenset(item.request for item in evidence),
    )

