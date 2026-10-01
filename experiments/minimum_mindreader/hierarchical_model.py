"""Canonical serialized artifact for the first learned SPI hierarchy."""

from __future__ import annotations

from dataclasses import dataclass

from known_protocol_corpus import BenchmarkCase
from model import TimedResponse
from protocol_program import ProtocolProgram
from spi_behavior import SpiBehaviorCandidate, infer_spi_behavior
from spi_hypothesis import SpiBitOrder, SpiHypothesis, SpiSamplingEdge


MAGIC = b"DP"
FORMAT_VERSION = 1
PROTOCOL_KIND_SPI = 1
HEADER_BYTES = 12
FLAG_SELECT_ACTIVE = 1 << 0
FLAG_CLOCK_IDLE = 1 << 1
FLAG_SAMPLE_TRAILING = 1 << 2
FLAG_BIT_REVERSE_EQUIVALENT = 1 << 3


@dataclass(frozen=True)
class SpiPhysicalModel:
    select_pin: int
    clock_pin: int
    request_pin: int
    response_pin: int
    select_active_level: int
    clock_idle_level: int
    sampling_edge: SpiSamplingEdge
    word_bits: int

    def __post_init__(self) -> None:
        pins = (self.select_pin, self.clock_pin, self.request_pin, self.response_pin)
        if len(set(pins)) != 4 or any(not 0 <= pin < 4 for pin in pins):
            raise ValueError("SPI physical model requires four distinct two-bit pins")
        if self.select_active_level not in (0, 1):
            raise ValueError("select active level must be binary")
        if self.clock_idle_level not in (0, 1):
            raise ValueError("clock idle level must be binary")
        if not 1 <= self.word_bits <= 0xFF:
            raise ValueError("word_bits must fit in one byte")

    def canonical_hypothesis(self) -> SpiHypothesis:
        return SpiHypothesis(
            select_pin=self.select_pin,
            clock_pin=self.clock_pin,
            data_a_pin=self.request_pin,
            data_b_pin=self.response_pin,
            select_active_level=self.select_active_level,
            clock_idle_level=self.clock_idle_level,
            sampling_edge=self.sampling_edge,
            bit_order=SpiBitOrder.MSB_FIRST,
        )


@dataclass(frozen=True)
class ModelProvenance:
    waveform_count: int
    physical_hypotheses_per_waveform: int
    equivalent_survivors: int

    def __post_init__(self) -> None:
        if not 1 <= self.waveform_count <= 0xFF:
            raise ValueError("waveform_count must fit in one byte")
        if not 1 <= self.physical_hypotheses_per_waveform <= 0xFFFF:
            raise ValueError("physical hypothesis count must fit in two bytes")
        if not 1 <= self.equivalent_survivors <= 0xFF:
            raise ValueError("equivalent survivor count must fit in one byte")

    @property
    def physical_evaluations(self) -> int:
        return self.waveform_count * self.physical_hypotheses_per_waveform


@dataclass(frozen=True)
class HierarchicalSpiModel:
    physical: SpiPhysicalModel
    program: ProtocolProgram
    provenance: ModelProvenance
    bit_reverse_equivalent: bool

    @property
    def encoded_bytes(self) -> int:
        return len(self.encode())

    @property
    def storage_bits(self) -> int:
        return self.encoded_bytes * 8

    def emulate_decoded(self, request: int) -> TimedResponse | None:
        return self.program.new_emulator().emulate(request)

    def encode(self) -> bytes:
        program = self.program.encode()
        if len(program) > 0xFF:
            raise ValueError("program is too large for the first hierarchy format")
        flags = 0
        if self.physical.select_active_level:
            flags |= FLAG_SELECT_ACTIVE
        if self.physical.clock_idle_level:
            flags |= FLAG_CLOCK_IDLE
        if self.physical.sampling_edge is SpiSamplingEdge.TRAILING:
            flags |= FLAG_SAMPLE_TRAILING
        if self.bit_reverse_equivalent:
            flags |= FLAG_BIT_REVERSE_EQUIVALENT
        pin_map = (
            self.physical.select_pin
            | (self.physical.clock_pin << 2)
            | (self.physical.request_pin << 4)
            | (self.physical.response_pin << 6)
        )
        header = (
            MAGIC
            + bytes(
                (
                    FORMAT_VERSION,
                    PROTOCOL_KIND_SPI,
                    flags,
                    pin_map,
                    self.physical.word_bits,
                    self.provenance.waveform_count,
                )
            )
            + self.provenance.physical_hypotheses_per_waveform.to_bytes(2, "little")
            + bytes((self.provenance.equivalent_survivors, len(program)))
        )
        return header + program

    @classmethod
    def decode(cls, data: bytes) -> "HierarchicalSpiModel":
        if len(data) < HEADER_BYTES:
            raise ValueError("hierarchical model is shorter than its header")
        if data[:2] != MAGIC:
            raise ValueError("invalid hierarchical model magic")
        if data[2] != FORMAT_VERSION:
            raise ValueError("unsupported hierarchical model version")
        if data[3] != PROTOCOL_KIND_SPI:
            raise ValueError("hierarchical model is not SPI")
        flags = data[4]
        pin_map = data[5]
        program_length = data[11]
        if len(data) != HEADER_BYTES + program_length:
            raise ValueError("hierarchical model length does not match its header")
        physical = SpiPhysicalModel(
            select_pin=pin_map & 0x03,
            clock_pin=(pin_map >> 2) & 0x03,
            request_pin=(pin_map >> 4) & 0x03,
            response_pin=(pin_map >> 6) & 0x03,
            select_active_level=1 if flags & FLAG_SELECT_ACTIVE else 0,
            clock_idle_level=1 if flags & FLAG_CLOCK_IDLE else 0,
            sampling_edge=(
                SpiSamplingEdge.TRAILING
                if flags & FLAG_SAMPLE_TRAILING
                else SpiSamplingEdge.LEADING
            ),
            word_bits=data[6],
        )
        provenance = ModelProvenance(
            waveform_count=data[7],
            physical_hypotheses_per_waveform=int.from_bytes(data[8:10], "little"),
            equivalent_survivors=data[10],
        )
        return cls(
            physical=physical,
            program=ProtocolProgram.decode(data[HEADER_BYTES:]),
            provenance=provenance,
            bit_reverse_equivalent=bool(flags & FLAG_BIT_REVERSE_EQUIVALENT),
        )

    def describe(self) -> dict[str, object]:
        return {
            "format_bytes": self.encoded_bytes,
            "storage_bits": self.storage_bits,
            "physical": {
                "select_pin": self.physical.select_pin,
                "clock_pin": self.physical.clock_pin,
                "request_pin": self.physical.request_pin,
                "response_pin": self.physical.response_pin,
                "select_active_level": self.physical.select_active_level,
                "clock_idle_level": self.physical.clock_idle_level,
                "sampling_edge": self.physical.sampling_edge.value,
                "word_bits": self.physical.word_bits,
                "canonical_bit_order": SpiBitOrder.MSB_FIRST.value,
            },
            "equivalence": {"bit_reverse": self.bit_reverse_equivalent},
            "provenance": {
                "waveform_count": self.provenance.waveform_count,
                "hypotheses_per_waveform": self.provenance.physical_hypotheses_per_waveform,
                "physical_evaluations": self.provenance.physical_evaluations,
                "equivalent_survivors": self.provenance.equivalent_survivors,
            },
            "program_bytes": self.program.encoded_bytes,
        }


def _physical_key(candidate: SpiBehaviorCandidate) -> tuple[object, ...]:
    hypothesis = candidate.hypothesis
    return (
        hypothesis.select_pin,
        hypothesis.clock_pin,
        hypothesis.data_a_pin,
        hypothesis.data_b_pin,
        hypothesis.select_active_level,
        hypothesis.clock_idle_level,
        hypothesis.sampling_edge,
    )


def build_hierarchical_spi_model(
    cases: tuple[BenchmarkCase, ...],
) -> HierarchicalSpiModel:
    inference = infer_spi_behavior(cases)
    if len(inference.candidates) != 2:
        raise ValueError("SPI hierarchy requires direction resolved to two bit-order equivalents")
    if len({_physical_key(candidate) for candidate in inference.candidates}) != 1:
        raise ValueError("SPI candidates disagree on physical topology")
    if {candidate.hypothesis.bit_order for candidate in inference.candidates} != set(
        SpiBitOrder
    ):
        raise ValueError("SPI candidates are not a complete bit-order equivalence pair")

    canonical = next(
        candidate
        for candidate in inference.candidates
        if candidate.hypothesis.bit_order is SpiBitOrder.MSB_FIRST
    )
    hypothesis = canonical.hypothesis
    return HierarchicalSpiModel(
        physical=SpiPhysicalModel(
            select_pin=hypothesis.select_pin,
            clock_pin=hypothesis.clock_pin,
            request_pin=hypothesis.data_a_pin,
            response_pin=hypothesis.data_b_pin,
            select_active_level=hypothesis.select_active_level,
            clock_idle_level=hypothesis.clock_idle_level,
            sampling_edge=hypothesis.sampling_edge,
            word_bits=8,
        ),
        program=canonical.compile(),
        provenance=ModelProvenance(
            waveform_count=inference.waveform_count,
            physical_hypotheses_per_waveform=inference.physical_hypotheses_per_waveform,
            equivalent_survivors=len(inference.candidates),
        ),
        bit_reverse_equivalent=True,
    )
