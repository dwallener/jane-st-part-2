"""Scorer-only scenario vault for randomized interrogation tests.

Nothing in this module may be imported by synthesizable logic or by
``interrogation_harness``. Labels, target selections, and response oracles live
on this side of the Chinese Wall.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

from active_model import expand_hypotheses
from adversarial_corpus import run_adversarial_corpus
from interrogation_harness import (
    PublicInterrogationCase,
    RefusalCode,
    TransportCapability,
)
from known_protocol_corpus import benchmark_cases
from model import TimedResponse
from stateful_peripheral import training_sequences
from synthetic_peripheral import observe


@dataclass(frozen=True)
class OracleScenario:
    label: str
    public: PublicInterrogationCase
    exchange: Callable[[int], TimedResponse | None]
    should_resolve: bool
    expected_refusal: RefusalCode


def _must_not_probe(_: int) -> TimedResponse | None:
    raise AssertionError("safe-refusal scenario attempted an active probe")


def _passive_case(pin_count: int, samples: tuple[int, ...]) -> PublicInterrogationCase:
    return PublicInterrogationCase(
        anonymous_pin_count=pin_count,
        anonymous_samples=samples,
        transactions=(),
        capability=TransportCapability.PASSIVE_ONLY,
        electrically_admitted=False,
        stateful=False,
        allowed_requests=(),
    )


def make_template_scenario(secret_index: int) -> OracleScenario:
    """Create one invented protocol with secret response-bit wiring."""

    evidence = (observe(0xA0), observe(0xAF))
    public = PublicInterrogationCase(
        anonymous_pin_count=0,
        anonymous_samples=(),
        transactions=evidence,
        capability=TransportCapability.BYTE_REQUEST_RESPONSE,
        electrically_admitted=True,
        stateful=False,
        allowed_requests=tuple(range(0xA0, 0xB0)),
    )
    candidates = expand_hypotheses(evidence).candidates
    secret = candidates[secret_index % len(candidates)]
    return OracleScenario(
        label="invented_mask_template",
        public=public,
        exchange=secret.emulate,
        should_resolve=True,
        expected_refusal=RefusalCode.NONE,
    )


def scenario_suite(rng: Random) -> tuple[OracleScenario, ...]:
    scenarios: list[OracleScenario] = []

    # Current canonical frontends expose anonymous physical evidence but do not
    # yet provide a corpus-wide admitted active transport. Safe refusal is the
    # only correct result at this boundary.
    for case in benchmark_cases():
        evidence = case.inference_input()
        scenarios.append(
            OracleScenario(
                label=f"canonical:{case.name}",
                public=_passive_case(evidence.pin_count, evidence.samples),
                exchange=_must_not_probe,
                should_resolve=False,
                expected_refusal=RefusalCode.NO_ACTIVE_TRANSPORT,
            )
        )

    # Adversarial/invented corpus summaries remain passive until a scenario
    # supplies an executable action language and electrical contract.
    for result in run_adversarial_corpus():
        scenarios.append(
            OracleScenario(
                label=f"adversarial:{result.name}",
                public=_passive_case(
                    8,
                    (result.observations_required & 0xFF,
                     result.surviving_equivalence & 0xFF),
                ),
                exchange=_must_not_probe,
                should_resolve=False,
                expected_refusal=RefusalCode.NO_ACTIVE_TRANSPORT,
            )
        )

    scenarios.append(
        OracleScenario(
            label="invented:stateful_toggle",
            public=PublicInterrogationCase(
                anonymous_pin_count=0,
                anonymous_samples=(),
                transactions=training_sequences()[0],
                capability=TransportCapability.BYTE_REQUEST_RESPONSE,
                electrically_admitted=True,
                stateful=True,
                allowed_requests=tuple(range(0xA0, 0xB0)),
            ),
            exchange=_must_not_probe,
            should_resolve=False,
            expected_refusal=RefusalCode.STATEFUL_PROBE_UNSUPPORTED,
        )
    )
    scenarios.append(make_template_scenario(rng.randrange(256)))
    rng.shuffle(scenarios)
    return tuple(scenarios)
