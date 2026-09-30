"""Protocol-neutral cycle-delta edge trace used by Experiment 001."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


PIN_MASK = 0xFF


class Marker(str, Enum):
    REQUEST_START = "request_start"
    REQUEST_END = "request_end"
    RESPONSE_START = "response_start"
    RESPONSE_END = "response_end"


@dataclass(frozen=True)
class TraceEvent:
    delta_cycles: int
    input_value: int
    input_changed: int
    output_value: int
    output_changed: int
    marker: Marker | None = None

    def __post_init__(self) -> None:
        if self.delta_cycles < 0:
            raise ValueError("delta_cycles must be non-negative")
        for name in (
            "input_value",
            "input_changed",
            "output_value",
            "output_changed",
        ):
            value = getattr(self, name)
            if not 0 <= value <= PIN_MASK:
                raise ValueError(f"{name} must be an 8-bit value")


@dataclass(frozen=True)
class Trace:
    events: tuple[TraceEvent, ...]

    def __post_init__(self) -> None:
        previous_input = 0
        previous_output = 0
        for index, event in enumerate(self.events):
            expected_input_changed = previous_input ^ event.input_value
            expected_output_changed = previous_output ^ event.output_value
            if event.input_changed != expected_input_changed:
                raise ValueError(
                    f"event {index} input_changed is 0x{event.input_changed:02X}; "
                    f"expected 0x{expected_input_changed:02X}"
                )
            if event.output_changed != expected_output_changed:
                raise ValueError(
                    f"event {index} output_changed is 0x{event.output_changed:02X}; "
                    f"expected 0x{expected_output_changed:02X}"
                )
            if (
                event.input_changed == 0
                and event.output_changed == 0
                and event.marker is None
            ):
                raise ValueError(f"event {index} has neither an edge nor a marker")
            previous_input = event.input_value
            previous_output = event.output_value

    @property
    def duration_cycles(self) -> int:
        return sum(event.delta_cycles for event in self.events)

    def to_csv(self) -> str:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "delta_cycles",
                "input_value",
                "input_changed",
                "output_value",
                "output_changed",
                "marker",
            ),
        )
        writer.writeheader()
        for event in self.events:
            writer.writerow(
                {
                    "delta_cycles": event.delta_cycles,
                    "input_value": f"0x{event.input_value:02X}",
                    "input_changed": f"0x{event.input_changed:02X}",
                    "output_value": f"0x{event.output_value:02X}",
                    "output_changed": f"0x{event.output_changed:02X}",
                    "marker": event.marker.value if event.marker is not None else "",
                }
            )
        return stream.getvalue()

    @classmethod
    def from_csv(cls, text: str) -> "Trace":
        reader = csv.DictReader(io.StringIO(text))
        expected_fields = [
            "delta_cycles",
            "input_value",
            "input_changed",
            "output_value",
            "output_changed",
            "marker",
        ]
        if reader.fieldnames != expected_fields:
            raise ValueError("unexpected trace CSV header")

        events: list[TraceEvent] = []
        for row in reader:
            marker_text = row["marker"]
            events.append(
                TraceEvent(
                    delta_cycles=int(row["delta_cycles"]),
                    input_value=int(row["input_value"], 0),
                    input_changed=int(row["input_changed"], 0),
                    output_value=int(row["output_value"], 0),
                    output_changed=int(row["output_changed"], 0),
                    marker=Marker(marker_text) if marker_text else None,
                )
            )
        return cls(tuple(events))


class TraceBuilder:
    """Build canonical edge events while accumulating edge-free time."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self._input_value = 0
        self._output_value = 0
        self._pending_cycles = 0

    @property
    def input_value(self) -> int:
        return self._input_value

    @property
    def output_value(self) -> int:
        return self._output_value

    def wait(self, cycles: int) -> None:
        if cycles < 0:
            raise ValueError("wait cycles must be non-negative")
        self._pending_cycles += cycles

    def emit(
        self,
        *,
        input_value: int | None = None,
        output_value: int | None = None,
        marker: Marker | None = None,
    ) -> None:
        next_input = self._input_value if input_value is None else input_value
        next_output = self._output_value if output_value is None else output_value
        input_changed = self._input_value ^ next_input
        output_changed = self._output_value ^ next_output
        event = TraceEvent(
            delta_cycles=self._pending_cycles,
            input_value=next_input,
            input_changed=input_changed,
            output_value=next_output,
            output_changed=output_changed,
            marker=marker,
        )
        if input_changed == 0 and output_changed == 0 and marker is None:
            raise ValueError("cannot emit an event with neither an edge nor a marker")
        self._events.append(event)
        self._input_value = next_input
        self._output_value = next_output
        self._pending_cycles = 0

    def build(self) -> Trace:
        if self._pending_cycles:
            raise ValueError("trace ends with unrecorded edge-free time")
        return Trace(tuple(self._events))


def concatenate(traces: Iterable[Trace], gap_cycles: int = 1) -> Trace:
    """Concatenate zero-terminated traces while preserving delta timing."""

    if gap_cycles < 0:
        raise ValueError("gap_cycles must be non-negative")
    events: list[TraceEvent] = []
    for trace in traces:
        if not trace.events:
            continue
        if events:
            first = trace.events[0]
            first = TraceEvent(
                delta_cycles=first.delta_cycles + gap_cycles,
                input_value=first.input_value,
                input_changed=first.input_changed,
                output_value=first.output_value,
                output_changed=first.output_changed,
                marker=first.marker,
            )
            events.append(first)
            events.extend(trace.events[1:])
        else:
            events.extend(trace.events)
    return Trace(tuple(events))


def strip_markers(trace: Trace) -> Trace:
    """Remove annotations while preserving absolute edge timing."""

    events: list[TraceEvent] = []
    carried_cycles = 0
    for event in trace.events:
        delta_cycles = event.delta_cycles + carried_cycles
        carried_cycles = 0
        if event.input_changed == 0 and event.output_changed == 0:
            carried_cycles = delta_cycles
            continue
        events.append(
            TraceEvent(
                delta_cycles=delta_cycles,
                input_value=event.input_value,
                input_changed=event.input_changed,
                output_value=event.output_value,
                output_changed=event.output_changed,
                marker=None,
            )
        )
    if carried_cycles:
        raise ValueError("cannot preserve trailing marker-only time")
    return Trace(tuple(events))
