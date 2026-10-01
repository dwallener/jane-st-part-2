"""Bounded anonymous-pin SPI topology and convention inference."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import permutations

from known_protocol_corpus import DigitalWaveform


class SpiSamplingEdge(Enum):
    LEADING = "leading"
    TRAILING = "trailing"


class SpiBitOrder(Enum):
    MSB_FIRST = "msb_first"
    LSB_FIRST = "lsb_first"


@dataclass(frozen=True)
class SpiHypothesis:
    select_pin: int
    clock_pin: int
    data_a_pin: int
    data_b_pin: int
    select_active_level: int
    clock_idle_level: int
    sampling_edge: SpiSamplingEdge
    bit_order: SpiBitOrder


@dataclass(frozen=True)
class SpiCandidate:
    hypothesis: SpiHypothesis
    data_a_word: int
    data_b_word: int


@dataclass(frozen=True)
class SpiInference:
    candidates: tuple[SpiCandidate, ...]
    hypothesis_count: int

    @property
    def select_pins(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(item.hypothesis.select_pin for item in self.candidates))

    @property
    def clock_pins(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(item.hypothesis.clock_pin for item in self.candidates))

    @property
    def select_active_levels(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.select_active_level for item in self.candidates)
        )

    @property
    def clock_idle_levels(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.clock_idle_level for item in self.candidates)
        )

    @property
    def sampling_edges(self) -> tuple[SpiSamplingEdge, ...]:
        return tuple(
            dict.fromkeys(item.hypothesis.sampling_edge for item in self.candidates)
        )

    @property
    def bit_orders(self) -> tuple[SpiBitOrder, ...]:
        return tuple(dict.fromkeys(item.hypothesis.bit_order for item in self.candidates))

    @property
    def unordered_data_pin_pairs(self) -> tuple[frozenset[int], ...]:
        return tuple(
            dict.fromkeys(
                frozenset((item.hypothesis.data_a_pin, item.hypothesis.data_b_pin))
                for item in self.candidates
            )
        )


def _level(sample: int, pin: int) -> int:
    return (sample >> pin) & 1


def _assemble(bits: list[int], bit_order: SpiBitOrder) -> int:
    if bit_order is SpiBitOrder.MSB_FIRST:
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return value
    return sum(bit << index for index, bit in enumerate(bits))


def decode_spi_hypothesis(
    waveform: DigitalWaveform,
    hypothesis: SpiHypothesis,
    *,
    word_bits: int = 8,
) -> tuple[int, int]:
    if word_bits < 1:
        raise ValueError("word_bits must be positive")
    pins = (
        hypothesis.select_pin,
        hypothesis.clock_pin,
        hypothesis.data_a_pin,
        hypothesis.data_b_pin,
    )
    if len(set(pins)) != 4 or any(not 0 <= pin < waveform.pin_count for pin in pins):
        raise ValueError("SPI roles must use four distinct waveform pins")
    if hypothesis.select_active_level not in (0, 1):
        raise ValueError("select active level must be binary")
    if hypothesis.clock_idle_level not in (0, 1):
        raise ValueError("clock idle level must be binary")

    initial = waveform.samples[0]
    final = waveform.samples[-1]
    inactive_level = hypothesis.select_active_level ^ 1
    if _level(initial, hypothesis.select_pin) != inactive_level:
        raise ValueError("select is not initially inactive")
    if _level(final, hypothesis.select_pin) != inactive_level:
        raise ValueError("select is not finally inactive")
    if _level(initial, hypothesis.clock_pin) != hypothesis.clock_idle_level:
        raise ValueError("clock does not begin at the proposed idle level")
    if _level(final, hypothesis.clock_pin) != hypothesis.clock_idle_level:
        raise ValueError("clock does not end at the proposed idle level")

    select_transitions = 0
    selected = False
    saw_selected_clock = False
    data_a_bits: list[int] = []
    data_b_bits: list[int] = []
    previous = initial

    for sample in waveform.samples[1:]:
        previous_select = _level(previous, hypothesis.select_pin)
        select = _level(sample, hypothesis.select_pin)
        previous_clock = _level(previous, hypothesis.clock_pin)
        clock = _level(sample, hypothesis.clock_pin)
        changed = previous ^ sample

        if select != previous_select:
            select_transitions += 1
            if select == hypothesis.select_active_level:
                if selected:
                    raise ValueError("select asserted more than once")
                selected = True
            else:
                if not selected:
                    raise ValueError("select deasserted before assertion")
                selected = False

        clock_changed = clock != previous_clock
        if clock_changed and not selected:
            raise ValueError("clock changed while select was inactive")
        if clock_changed and selected:
            saw_selected_clock = True
            leading = (
                previous_clock == hypothesis.clock_idle_level
                and clock == (hypothesis.clock_idle_level ^ 1)
            )
            trailing = (
                previous_clock == (hypothesis.clock_idle_level ^ 1)
                and clock == hypothesis.clock_idle_level
            )
            sample_now = (
                leading
                if hypothesis.sampling_edge is SpiSamplingEdge.LEADING
                else trailing
            )
            if sample_now:
                data_mask = (1 << hypothesis.data_a_pin) | (
                    1 << hypothesis.data_b_pin
                )
                if changed & data_mask:
                    raise ValueError("data changes on candidate sampling edge")
                data_a_bits.append(_level(sample, hypothesis.data_a_pin))
                data_b_bits.append(_level(sample, hypothesis.data_b_pin))
        previous = sample

    if select_transitions != 2 or selected:
        raise ValueError("waveform does not contain exactly one selected transfer")
    if not saw_selected_clock:
        raise ValueError("selected transfer contains no clock edges")
    if len(data_a_bits) != word_bits or len(data_b_bits) != word_bits:
        raise ValueError("selected transfer has the wrong sampled word width")
    return (
        _assemble(data_a_bits, hypothesis.bit_order),
        _assemble(data_b_bits, hypothesis.bit_order),
    )


def infer_spi(waveform: DigitalWaveform, *, word_bits: int = 8) -> SpiInference:
    if waveform.pin_count != 4:
        raise ValueError("first SPI search requires exactly four pins")

    candidates: list[SpiCandidate] = []
    hypothesis_count = 0
    for select_pin, clock_pin, data_a_pin, data_b_pin in permutations(range(4)):
        for select_active_level in (0, 1):
            for clock_idle_level in (0, 1):
                for sampling_edge in SpiSamplingEdge:
                    for bit_order in SpiBitOrder:
                        hypothesis_count += 1
                        hypothesis = SpiHypothesis(
                            select_pin=select_pin,
                            clock_pin=clock_pin,
                            data_a_pin=data_a_pin,
                            data_b_pin=data_b_pin,
                            select_active_level=select_active_level,
                            clock_idle_level=clock_idle_level,
                            sampling_edge=sampling_edge,
                            bit_order=bit_order,
                        )
                        try:
                            data_a_word, data_b_word = decode_spi_hypothesis(
                                waveform, hypothesis, word_bits=word_bits
                            )
                        except ValueError:
                            continue
                        candidates.append(
                            SpiCandidate(hypothesis, data_a_word, data_b_word)
                        )
    return SpiInference(tuple(candidates), hypothesis_count)
