"""Label-free active-interrogation policy boundary.

This module deliberately contains no protocol corpus, golden truth, or target
implementation. It can see only public evidence and a response callback that
behaves like an electrically admitted transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from active_model import expand_hypotheses
from model import TimedResponse, Transaction


class TransportCapability(Enum):
    PASSIVE_ONLY = 0
    BYTE_REQUEST_RESPONSE = 1


class RefusalCode(Enum):
    NONE = 0
    NO_ACTIVE_TRANSPORT = 1
    ELECTRICAL_NOT_ADMITTED = 2
    STATEFUL_PROBE_UNSUPPORTED = 3
    CANDIDATE_CAPACITY = 4
    NO_DISTINGUISHING_PROBE = 5
    CONTRADICTORY_RESPONSE = 6
    PROBE_BUDGET = 7


@dataclass(frozen=True)
class PublicInterrogationCase:
    """Everything the policy may know before issuing a probe.

    Anonymous samples are retained for passive-only scenarios so the harness
    cannot accidentally replace "unsupported" with "no evidence." They carry
    no family name, role name, scorer label, or target selection.
    """

    anonymous_pin_count: int
    anonymous_samples: tuple[int, ...]
    transactions: tuple[Transaction, ...]
    capability: TransportCapability
    electrically_admitted: bool
    stateful: bool
    allowed_requests: tuple[int, ...]
    max_candidates: int = 4096
    max_probes: int = 8

    def __post_init__(self) -> None:
        if self.anonymous_pin_count < 0:
            raise ValueError("anonymous_pin_count must be non-negative")
        if self.anonymous_samples and self.anonymous_pin_count == 0:
            raise ValueError("samples require a positive anonymous pin count")
        sample_limit = 1 << self.anonymous_pin_count
        if any(not 0 <= sample < sample_limit for sample in self.anonymous_samples):
            raise ValueError("anonymous sample exceeds declared pin width")
        if any(not 0 <= request <= 0xFF for request in self.allowed_requests):
            raise ValueError("allowed requests must be bytes")
        if self.max_candidates < 1 or self.max_probes < 1:
            raise ValueError("resource bounds must be positive")


@dataclass(frozen=True)
class InterrogationResult:
    resolved: bool
    refusal: RefusalCode
    probes: tuple[int, ...]
    survivor_count: int


Exchange = Callable[[int], TimedResponse | None]


def interrogate(
    public: PublicInterrogationCase,
    exchange: Exchange,
) -> InterrogationResult:
    """Resolve a bounded candidate set or return an explicit safe refusal."""

    if public.capability is not TransportCapability.BYTE_REQUEST_RESPONSE:
        return InterrogationResult(False, RefusalCode.NO_ACTIVE_TRANSPORT, (), 0)
    if not public.electrically_admitted:
        return InterrogationResult(False, RefusalCode.ELECTRICAL_NOT_ADMITTED, (), 0)
    if public.stateful:
        return InterrogationResult(
            False, RefusalCode.STATEFUL_PROBE_UNSUPPORTED, (), 0
        )
    try:
        hypotheses = expand_hypotheses(
            public.transactions, max_candidates=public.max_candidates
        )
    except ValueError as error:
        if "more than" in str(error):
            return InterrogationResult(
                False, RefusalCode.CANDIDATE_CAPACITY, (), 0
            )
        raise

    probes: list[int] = []
    for _ in range(public.max_probes):
        if hypotheses.is_resolved:
            return InterrogationResult(True, RefusalCode.NONE, tuple(probes), 1)
        if hypotheses.is_contradictory:
            return InterrogationResult(
                False, RefusalCode.CONTRADICTORY_RESPONSE, tuple(probes), 0
            )
        suggestion = hypotheses.suggest_probe(public.allowed_requests)
        if suggestion is None:
            return InterrogationResult(
                False,
                RefusalCode.NO_DISTINGUISHING_PROBE,
                tuple(probes),
                len(hypotheses.candidates),
            )
        probes.append(suggestion.request)
        response = exchange(suggestion.request)
        if response is None:
            return InterrogationResult(
                False,
                RefusalCode.CONTRADICTORY_RESPONSE,
                tuple(probes),
                0,
            )
        hypotheses = hypotheses.observe(suggestion.request, response)

    if hypotheses.is_resolved:
        return InterrogationResult(True, RefusalCode.NONE, tuple(probes), 1)
    return InterrogationResult(
        False,
        RefusalCode.PROBE_BUDGET,
        tuple(probes),
        len(hypotheses.candidates),
    )
