"""Bounded one-byte integrity-rule inference for framed byte sequences."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


Payload = tuple[int, ...]
Frame = tuple[int, ...]


def _validate_bytes(values: tuple[int, ...], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError(f"{name} must contain only bytes")


class IntegrityKind(Enum):
    CONSTANT = "constant"
    XOR8 = "xor8"
    SUM8 = "sum8"
    NEGATIVE_SUM8 = "negative_sum8"
    CRC8 = "crc8"


class IntegrityModel(Protocol):
    kind: IntegrityKind

    def compute(self, payload: Payload) -> int: ...

    def describe(self) -> dict[str, int | str | bool]: ...


@dataclass(frozen=True)
class ConstantTrailer:
    value: int
    kind: IntegrityKind = IntegrityKind.CONSTANT

    def compute(self, payload: Payload) -> int:
        _validate_bytes(payload, "payload")
        return self.value

    def describe(self) -> dict[str, int | str | bool]:
        return {"kind": self.kind.value, "value": self.value}


@dataclass(frozen=True)
class Xor8:
    kind: IntegrityKind = IntegrityKind.XOR8

    def compute(self, payload: Payload) -> int:
        _validate_bytes(payload, "payload")
        result = 0
        for value in payload:
            result ^= value
        return result

    def describe(self) -> dict[str, int | str | bool]:
        return {"kind": self.kind.value}


@dataclass(frozen=True)
class Sum8:
    kind: IntegrityKind = IntegrityKind.SUM8

    def compute(self, payload: Payload) -> int:
        _validate_bytes(payload, "payload")
        return sum(payload) & 0xFF

    def describe(self) -> dict[str, int | str | bool]:
        return {"kind": self.kind.value}


@dataclass(frozen=True)
class NegativeSum8:
    kind: IntegrityKind = IntegrityKind.NEGATIVE_SUM8

    def compute(self, payload: Payload) -> int:
        _validate_bytes(payload, "payload")
        return (-sum(payload)) & 0xFF

    def describe(self) -> dict[str, int | str | bool]:
        return {"kind": self.kind.value}


def _reflect_byte(value: int) -> int:
    reflected = 0
    for bit in range(8):
        reflected |= ((value >> bit) & 1) << (7 - bit)
    return reflected


@dataclass(frozen=True)
class Crc8:
    name: str
    polynomial: int
    initial: int
    reflected: bool
    xor_output: int
    kind: IntegrityKind = IntegrityKind.CRC8

    def compute(self, payload: Payload) -> int:
        _validate_bytes(payload, "payload")
        crc = self.initial
        if self.reflected:
            reflected_polynomial = _reflect_byte(self.polynomial)
            for value in payload:
                crc ^= value
                for _ in range(8):
                    crc = (
                        (crc >> 1) ^ reflected_polynomial
                        if crc & 1
                        else crc >> 1
                    )
        else:
            for value in payload:
                crc ^= value
                for _ in range(8):
                    crc = (
                        ((crc << 1) ^ self.polynomial) & 0xFF
                        if crc & 0x80
                        else (crc << 1) & 0xFF
                    )
        return crc ^ self.xor_output

    def describe(self) -> dict[str, int | str | bool]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "polynomial": self.polynomial,
            "initial": self.initial,
            "reflected": self.reflected,
            "xor_output": self.xor_output,
        }


CRC8_CATALOG = (
    Crc8("CRC-8/SMBUS", 0x07, 0x00, False, 0x00),
    Crc8("CRC-8/SAE-J1850", 0x1D, 0xFF, False, 0xFF),
    Crc8("CRC-8/MAXIM-DOW", 0x31, 0x00, True, 0x00),
    Crc8("CRC-8/ROHC", 0x07, 0xFF, True, 0x00),
)


@dataclass(frozen=True)
class IntegrityProbe:
    payload: Payload
    predicted_trailers: tuple[int, ...]


@dataclass(frozen=True)
class IntegrityInference:
    candidates: tuple[IntegrityModel, ...]
    evidence_count: int

    @property
    def is_complete(self) -> bool:
        return len(self.candidates) == 1

    @property
    def model(self) -> IntegrityModel | None:
        return self.candidates[0] if self.is_complete else None

    @property
    def kinds(self) -> tuple[IntegrityKind, ...]:
        return tuple(candidate.kind for candidate in self.candidates)

    def propose_probe(self) -> IntegrityProbe | None:
        if len(self.candidates) < 2:
            return None
        for value in range(0x100):
            payload = (value,)
            predictions = tuple(
                candidate.compute(payload) for candidate in self.candidates
            )
            if len(set(predictions)) > 1:
                return IntegrityProbe(payload, predictions)
        return None


def frame_with_integrity(payload: Payload, model: IntegrityModel) -> Frame:
    _validate_bytes(payload, "payload")
    return payload + (model.compute(payload),)


def validate_frame(frame: Frame, model: IntegrityModel) -> bool:
    _validate_bytes(frame, "frame")
    if len(frame) < 2:
        raise ValueError("frame must contain payload and a one-byte trailer")
    return model.compute(frame[:-1]) == frame[-1]


def infer_integrity(
    frames: tuple[Frame, ...],
    *,
    crc_catalog: tuple[Crc8, ...] = CRC8_CATALOG,
) -> IntegrityInference:
    if not frames:
        raise ValueError("at least one frame is required")
    for frame in frames:
        _validate_bytes(frame, "frame")
        if len(frame) < 2:
            raise ValueError("frame must contain payload and a one-byte trailer")

    hypotheses: tuple[IntegrityModel, ...] = (
        ConstantTrailer(frames[0][-1]),
        Xor8(),
        Sum8(),
        NegativeSum8(),
        *crc_catalog,
    )
    candidates = tuple(
        hypothesis
        for hypothesis in hypotheses
        if all(validate_frame(frame, hypothesis) for frame in frames)
    )
    return IntegrityInference(candidates, len(frames))
