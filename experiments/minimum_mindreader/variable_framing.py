"""Bounded inference of length-prefixed versus delimiter-terminated frames."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


Frame = tuple[int, ...]


def _validate_bytes(values: tuple[int, ...], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError(f"{name} must contain only bytes")


class FramingKind(Enum):
    LENGTH = "length"
    DELIMITER = "delimiter"


class FramingModel(Protocol):
    kind: FramingKind

    def parse(self, stream: tuple[int, ...]) -> tuple[Frame, ...]: ...

    def describe(self) -> dict[str, int | str]: ...


@dataclass(frozen=True)
class LengthFraming:
    field_index: int
    total_bias: int
    maximum_frame_bytes: int
    kind: FramingKind = FramingKind.LENGTH

    def __post_init__(self) -> None:
        if self.field_index < 0:
            raise ValueError("field_index must be non-negative")
        if self.maximum_frame_bytes < 1:
            raise ValueError("maximum_frame_bytes must be positive")

    def parse(self, stream: tuple[int, ...]) -> tuple[Frame, ...]:
        _validate_bytes(stream, "stream")
        frames: list[Frame] = []
        offset = 0
        while offset < len(stream):
            field_position = offset + self.field_index
            if field_position >= len(stream):
                raise ValueError("stream ends before the length field")
            frame_bytes = stream[field_position] + self.total_bias
            if frame_bytes <= self.field_index:
                raise ValueError("length field does not include its own position")
            if frame_bytes > self.maximum_frame_bytes:
                raise ValueError("length field exceeds the configured frame bound")
            end = offset + frame_bytes
            if end > len(stream):
                raise ValueError("stream ends inside a length-prefixed frame")
            frames.append(stream[offset:end])
            offset = end
        return tuple(frames)

    def describe(self) -> dict[str, int | str]:
        return {
            "kind": self.kind.value,
            "field_index": self.field_index,
            "total_bias": self.total_bias,
            "maximum_frame_bytes": self.maximum_frame_bytes,
        }


@dataclass(frozen=True)
class DelimiterFraming:
    delimiter: int
    maximum_frame_bytes: int
    kind: FramingKind = FramingKind.DELIMITER

    def __post_init__(self) -> None:
        if not 0 <= self.delimiter <= 0xFF:
            raise ValueError("delimiter must be a byte")
        if self.maximum_frame_bytes < 1:
            raise ValueError("maximum_frame_bytes must be positive")

    def parse(self, stream: tuple[int, ...]) -> tuple[Frame, ...]:
        _validate_bytes(stream, "stream")
        frames: list[Frame] = []
        start = 0
        for index, value in enumerate(stream):
            if index - start + 1 > self.maximum_frame_bytes:
                raise ValueError("delimiter frame exceeds the configured bound")
            if value == self.delimiter:
                frames.append(stream[start : index + 1])
                start = index + 1
        if start != len(stream):
            raise ValueError("stream ends before a delimiter")
        return tuple(frames)

    def describe(self) -> dict[str, int | str]:
        return {
            "kind": self.kind.value,
            "delimiter": self.delimiter,
            "maximum_frame_bytes": self.maximum_frame_bytes,
        }


@dataclass(frozen=True)
class FramingInference:
    candidates: tuple[FramingModel, ...]
    evidence_count: int

    @property
    def is_complete(self) -> bool:
        return len(self.candidates) == 1

    @property
    def model(self) -> FramingModel | None:
        return self.candidates[0] if self.is_complete else None

    @property
    def kinds(self) -> tuple[FramingKind, ...]:
        return tuple(candidate.kind for candidate in self.candidates)


def _fits_training(model: FramingModel, frames: tuple[Frame, ...]) -> bool:
    stream = tuple(value for frame in frames for value in frame)
    try:
        return model.parse(stream) == frames
    except ValueError:
        return False


def learn_variable_framing(
    frames: tuple[Frame, ...],
    *,
    maximum_field_index: int = 3,
    minimum_bias: int = -8,
    maximum_bias: int = 8,
    maximum_frame_bytes: int = 64,
) -> FramingInference:
    if not frames:
        raise ValueError("at least one training frame is required")
    for frame in frames:
        _validate_bytes(frame, "training frame")
        if len(frame) > maximum_frame_bytes:
            raise ValueError("training frame exceeds the configured bound")
    if maximum_field_index < 0:
        raise ValueError("maximum_field_index must be non-negative")
    if minimum_bias > maximum_bias:
        raise ValueError("minimum_bias must not exceed maximum_bias")

    candidates: list[FramingModel] = []
    last_field_index = min(maximum_field_index, min(map(len, frames)) - 1)
    for field_index in range(last_field_index + 1):
        for total_bias in range(minimum_bias, maximum_bias + 1):
            candidate = LengthFraming(
                field_index, total_bias, maximum_frame_bytes
            )
            if _fits_training(candidate, frames):
                candidates.append(candidate)

    delimiter = frames[0][-1]
    delimiter_candidate = DelimiterFraming(delimiter, maximum_frame_bytes)
    if all(frame[-1] == delimiter and delimiter not in frame[:-1] for frame in frames):
        if _fits_training(delimiter_candidate, frames):
            candidates.append(delimiter_candidate)

    return FramingInference(tuple(candidates), len(frames))
