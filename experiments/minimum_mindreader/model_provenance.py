"""Compact evidence and uncertainty sidecar for learned protocol models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import IntEnum

from known_protocol_corpus import BenchmarkCase, DigitalWaveform
from spi_behavior import infer_spi_behavior


MAGIC = b"PV"
FORMAT_VERSION = 1
HEADER_BYTES = 8
MAX_EVIDENCE = 16


class ModelOrigin(IntEnum):
    LEARNED = 1
    HAND_AUTHORED = 2
    HOST_REFINED = 3


class ClaimKind(IntEnum):
    PHYSICAL_TOPOLOGY = 1
    DATA_DIRECTION = 2
    BEHAVIOR_TRANSITION = 3
    BIT_ORDER = 4


class ClaimStatus(IntEnum):
    SUPPORTED = 1
    EQUIVALENT = 2
    UNRESOLVED = 3


class ProbeKind(IntEnum):
    NONE = 0
    OBSERVE_DRIVE_OWNERSHIP = 1


@dataclass(frozen=True)
class EvidenceRecord:
    fingerprint: int

    def __post_init__(self) -> None:
        if not 0 <= self.fingerprint <= 0xFFFFFFFF:
            raise ValueError("evidence fingerprint must fit in 32 bits")


@dataclass(frozen=True)
class ProvenanceClaim:
    kind: ClaimKind
    status: ClaimStatus
    support_mask: int

    def __post_init__(self) -> None:
        if not 0 < self.support_mask <= 0xFFFF:
            raise ValueError("claim support mask must be a nonzero 16-bit value")


@dataclass(frozen=True)
class ProbeSuggestion:
    kind: ProbeKind
    payload: bytes = b""

    def __post_init__(self) -> None:
        if self.kind is ProbeKind.NONE and self.payload:
            raise ValueError("NONE probe must not contain a payload")
        if len(self.payload) > 0xFF:
            raise ValueError("probe payload must fit in one-byte length")


@dataclass(frozen=True)
class ProvenanceBundle:
    origin: ModelOrigin
    evidence: tuple[EvidenceRecord, ...]
    claims: tuple[ProvenanceClaim, ...]
    probe: ProbeSuggestion = ProbeSuggestion(ProbeKind.NONE)

    def __post_init__(self) -> None:
        if not 1 <= len(self.evidence) <= MAX_EVIDENCE:
            raise ValueError("provenance requires between one and sixteen evidence records")
        if not 1 <= len(self.claims) <= 0xFF:
            raise ValueError("provenance requires between one and 255 claims")
        valid_support = (1 << len(self.evidence)) - 1
        if any(claim.support_mask & ~valid_support for claim in self.claims):
            raise ValueError("claim references evidence outside the bundle")

    @property
    def encoded_bytes(self) -> int:
        return len(self.encode())

    def claim(self, kind: ClaimKind) -> ProvenanceClaim:
        matches = tuple(claim for claim in self.claims if claim.kind is kind)
        if len(matches) != 1:
            raise ValueError(f"expected exactly one {kind.name} claim")
        return matches[0]

    def supported_evidence(self, claim: ProvenanceClaim) -> tuple[EvidenceRecord, ...]:
        return tuple(
            record
            for index, record in enumerate(self.evidence)
            if claim.support_mask & (1 << index)
        )

    def encode(self) -> bytes:
        header = MAGIC + bytes(
            (
                FORMAT_VERSION,
                int(self.origin),
                len(self.evidence),
                len(self.claims),
                int(self.probe.kind),
                len(self.probe.payload),
            )
        )
        evidence = b"".join(
            record.fingerprint.to_bytes(4, "little") for record in self.evidence
        )
        claims = b"".join(
            bytes((int(claim.kind), int(claim.status)))
            + claim.support_mask.to_bytes(2, "little")
            for claim in self.claims
        )
        return header + evidence + claims + self.probe.payload

    @classmethod
    def decode(cls, data: bytes) -> "ProvenanceBundle":
        if len(data) < HEADER_BYTES:
            raise ValueError("provenance bundle is shorter than its header")
        if data[:2] != MAGIC:
            raise ValueError("invalid provenance magic")
        if data[2] != FORMAT_VERSION:
            raise ValueError("unsupported provenance version")
        evidence_count = data[4]
        claim_count = data[5]
        payload_length = data[7]
        expected_length = (
            HEADER_BYTES + evidence_count * 4 + claim_count * 4 + payload_length
        )
        if len(data) != expected_length:
            raise ValueError("provenance length does not match its header")
        offset = HEADER_BYTES
        evidence = tuple(
            EvidenceRecord(
                int.from_bytes(data[offset + index * 4 : offset + index * 4 + 4], "little")
            )
            for index in range(evidence_count)
        )
        offset += evidence_count * 4
        claims = tuple(
            ProvenanceClaim(
                ClaimKind(data[offset + index * 4]),
                ClaimStatus(data[offset + index * 4 + 1]),
                int.from_bytes(
                    data[offset + index * 4 + 2 : offset + index * 4 + 4],
                    "little",
                ),
            )
            for index in range(claim_count)
        )
        offset += claim_count * 4
        probe = ProbeSuggestion(
            ProbeKind(data[6]),
            data[offset : offset + payload_length],
        )
        return cls(ModelOrigin(data[3]), evidence, claims, probe)


def waveform_fingerprint(waveform: DigitalWaveform) -> int:
    if waveform.pin_count > 8:
        raise ValueError("first fingerprint format supports at most eight pins")
    if len(waveform.samples) > 0xFFFF:
        raise ValueError("first fingerprint format supports at most 65535 samples")
    canonical = (
        bytes((waveform.pin_count,))
        + len(waveform.samples).to_bytes(2, "little")
        + bytes(waveform.samples)
    )
    return int.from_bytes(hashlib.sha256(canonical).digest()[:4], "little")


def build_spi_provenance(cases: tuple[BenchmarkCase, ...]) -> ProvenanceBundle:
    if not cases:
        raise ValueError("at least one SPI case is required")
    if len(cases) > MAX_EVIDENCE:
        raise ValueError("first provenance format supports at most sixteen cases")
    inference = infer_spi_behavior(cases)
    evidence = tuple(
        EvidenceRecord(waveform_fingerprint(case.inference_input())) for case in cases
    )
    support_mask = (1 << len(evidence)) - 1

    if len(inference.candidates) == 2:
        direction_status = ClaimStatus.SUPPORTED
        behavior_status = ClaimStatus.SUPPORTED
        probe = ProbeSuggestion(ProbeKind.NONE)
    elif len(inference.candidates) == 4:
        direction_status = ClaimStatus.UNRESOLVED
        behavior_status = ClaimStatus.UNRESOLVED
        probe = ProbeSuggestion(ProbeKind.OBSERVE_DRIVE_OWNERSHIP)
    else:
        raise ValueError("SPI provenance requires two or four behavioral candidates")

    claims = (
        ProvenanceClaim(
            ClaimKind.PHYSICAL_TOPOLOGY, ClaimStatus.SUPPORTED, support_mask
        ),
        ProvenanceClaim(ClaimKind.DATA_DIRECTION, direction_status, support_mask),
        ProvenanceClaim(
            ClaimKind.BEHAVIOR_TRANSITION, behavior_status, support_mask
        ),
        ProvenanceClaim(ClaimKind.BIT_ORDER, ClaimStatus.EQUIVALENT, support_mask),
    )
    return ProvenanceBundle(ModelOrigin.LEARNED, evidence, claims, probe)
