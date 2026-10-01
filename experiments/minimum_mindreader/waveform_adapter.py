"""Lossless anonymous edge representation and corpus activity profiling."""

from __future__ import annotations

from dataclasses import dataclass

from known_protocol_corpus import BenchmarkCase, DigitalWaveform


@dataclass(frozen=True)
class AnonymousEdgeEvent:
    delta_cycles: int
    value: int
    changed: int

    def __post_init__(self) -> None:
        if self.delta_cycles < 1:
            raise ValueError("edge delta must be positive")
        if self.changed == 0:
            raise ValueError("edge event must change at least one pin")


@dataclass(frozen=True)
class AnonymousEdgeTrace:
    pin_count: int
    initial_value: int
    events: tuple[AnonymousEdgeEvent, ...]
    trailing_cycles: int

    def __post_init__(self) -> None:
        if self.pin_count < 1:
            raise ValueError("pin_count must be positive")
        if self.trailing_cycles < 0:
            raise ValueError("trailing_cycles must be non-negative")
        limit = 1 << self.pin_count
        if not 0 <= self.initial_value < limit:
            raise ValueError("initial value exceeds pin width")
        previous = self.initial_value
        for index, event in enumerate(self.events):
            if not 0 <= event.value < limit:
                raise ValueError(f"event {index} value exceeds pin width")
            if event.changed != (previous ^ event.value):
                raise ValueError(f"event {index} changed mask is inconsistent")
            previous = event.value

    @property
    def duration_cycles(self) -> int:
        return sum(event.delta_cycles for event in self.events) + self.trailing_cycles


@dataclass(frozen=True)
class PinActivity:
    pin_index: int
    initial_level: int
    final_level: int
    transition_count: int
    rising_edges: int
    falling_edges: int
    shortest_edge_interval: int | None
    longest_edge_interval: int | None


def compress_waveform(waveform: DigitalWaveform) -> AnonymousEdgeTrace:
    previous = waveform.samples[0]
    previous_edge_cycle = 0
    events: list[AnonymousEdgeEvent] = []
    for cycle, value in enumerate(waveform.samples[1:], start=1):
        changed = previous ^ value
        if changed:
            events.append(
                AnonymousEdgeEvent(
                    delta_cycles=cycle - previous_edge_cycle,
                    value=value,
                    changed=changed,
                )
            )
            previous_edge_cycle = cycle
            previous = value
    trailing_cycles = len(waveform.samples) - 1 - previous_edge_cycle
    return AnonymousEdgeTrace(
        pin_count=waveform.pin_count,
        initial_value=waveform.samples[0],
        events=tuple(events),
        trailing_cycles=trailing_cycles,
    )


def expand_edge_trace(trace: AnonymousEdgeTrace) -> DigitalWaveform:
    samples = [trace.initial_value]
    previous = trace.initial_value
    for event in trace.events:
        samples.extend([previous] * (event.delta_cycles - 1))
        samples.append(event.value)
        previous = event.value
    samples.extend([previous] * trace.trailing_cycles)
    return DigitalWaveform(trace.pin_count, tuple(samples))


def profile_pins(trace: AnonymousEdgeTrace) -> tuple[PinActivity, ...]:
    absolute_cycle = 0
    edge_cycles: list[list[int]] = [[] for _ in range(trace.pin_count)]
    rising = [0] * trace.pin_count
    falling = [0] * trace.pin_count
    previous = trace.initial_value

    for event in trace.events:
        absolute_cycle += event.delta_cycles
        for pin in range(trace.pin_count):
            mask = 1 << pin
            if event.changed & mask:
                edge_cycles[pin].append(absolute_cycle)
                if event.value & mask:
                    rising[pin] += 1
                else:
                    falling[pin] += 1
        previous = event.value

    activities: list[PinActivity] = []
    for pin in range(trace.pin_count):
        cycles = edge_cycles[pin]
        intervals = [right - left for left, right in zip(cycles, cycles[1:])]
        activities.append(
            PinActivity(
                pin_index=pin,
                initial_level=(trace.initial_value >> pin) & 1,
                final_level=(previous >> pin) & 1,
                transition_count=len(cycles),
                rising_edges=rising[pin],
                falling_edges=falling[pin],
                shortest_edge_interval=min(intervals) if intervals else None,
                longest_edge_interval=max(intervals) if intervals else None,
            )
        )
    return tuple(activities)


@dataclass(frozen=True)
class LayerResult:
    layer: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class BenchmarkScore:
    case_name: str
    family: str
    layers: tuple[LayerResult, ...]

    @property
    def deepest_passed_layer(self) -> str:
        passed = [result.layer for result in self.layers if result.passed]
        return passed[-1] if passed else "none"


def _frontend_gap(case: BenchmarkCase) -> str:
    if case.truth.family == "SPI":
        return (
            "current frontend requires active-high select and a separate "
            "response-valid phase; SPI uses active-low selection and simultaneous data"
        )
    if case.truth.family == "UART":
        return (
            "current frontend requires external clock and select pins; "
            "UART timing is recovered from one asynchronous data line"
        )
    if case.truth.family == "I2C":
        return (
            "current frontend requires separate request and response pins; "
            "I2C uses shared bidirectional open-drain data and in-band ACK"
        )
    return "protocol topology is outside the current selected serial frontend"


def score_current_frontend(case: BenchmarkCase) -> BenchmarkScore:
    edge_trace = compress_waveform(case.inference_input())
    round_trip = expand_edge_trace(edge_trace) == case.inference_input()
    activities = profile_pins(edge_trace)
    profile_ok = len(activities) == case.waveform.pin_count
    return BenchmarkScore(
        case_name=case.name,
        family=case.truth.family,
        layers=(
            LayerResult(
                "capture",
                round_trip,
                "anonymous waveform round-trips losslessly"
                if round_trip
                else "edge compression changed the waveform",
            ),
            LayerResult(
                "activity_profile",
                profile_ok,
                "per-pin transitions and edge intervals extracted"
                if profile_ok
                else "pin activity extraction failed",
            ),
            LayerResult("current_frontend", False, _frontend_gap(case)),
        ),
    )
