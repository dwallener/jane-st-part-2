"""Small golden waveform corpus for established digital protocols."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DigitalWaveform:
    pin_count: int
    samples: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.pin_count < 1:
            raise ValueError("pin_count must be positive")
        if not self.samples:
            raise ValueError("waveform must contain samples")
        limit = 1 << self.pin_count
        if any(not 0 <= sample < limit for sample in self.samples):
            raise ValueError("sample contains a value outside the pin width")

    def level(self, sample_index: int, pin_index: int) -> int:
        if not 0 <= pin_index < self.pin_count:
            raise ValueError("pin index is outside the waveform")
        return (self.samples[sample_index] >> pin_index) & 1


@dataclass(frozen=True)
class ProtocolTruth:
    family: str
    parameters: tuple[tuple[str, str], ...]
    pin_roles: tuple[tuple[str, int], ...]
    expected_input_symbols: tuple[int, ...]
    expected_output_symbols: tuple[int, ...] = ()
    expected_ack_bits: tuple[int, ...] = ()

    def parameter(self, name: str) -> str:
        return dict(self.parameters)[name]

    def pin(self, role: str) -> int:
        return dict(self.pin_roles)[role]


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    waveform: DigitalWaveform
    truth: ProtocolTruth

    def inference_input(self) -> DigitalWaveform:
        """Return only anonymous indexed-pin evidence."""
        return self.waveform


def _set_pin(sample: int, pin: int, value: int) -> int:
    return sample | (1 << pin) if value else sample & ~(1 << pin)


def _temporal_bits(value: int, msb_first: bool) -> tuple[int, ...]:
    indices = reversed(range(8)) if msb_first else range(8)
    return tuple((value >> index) & 1 for index in indices)


SPI_CLOCK = 0
SPI_MOSI = 1
SPI_MISO = 2
SPI_SELECT_N = 3


def make_spi_case(
    mode: int,
    msb_first: bool,
    request: int = 0xA6,
    response: int = 0x3C,
) -> BenchmarkCase:
    if mode not in range(4):
        raise ValueError("SPI mode must be in the range 0..3")
    cpol = mode >> 1
    cpha = mode & 1
    request_bits = _temporal_bits(request, msb_first)
    response_bits = _temporal_bits(response, msb_first)

    sample = 0
    sample = _set_pin(sample, SPI_CLOCK, cpol)
    sample = _set_pin(sample, SPI_SELECT_N, 1)
    samples = [sample]
    sample = _set_pin(sample, SPI_SELECT_N, 0)
    if not cpha:
        sample = _set_pin(sample, SPI_MOSI, request_bits[0])
        sample = _set_pin(sample, SPI_MISO, response_bits[0])
    samples.append(sample)

    for index, (request_bit, response_bit) in enumerate(
        zip(request_bits, response_bits)
    ):
        sample = _set_pin(sample, SPI_CLOCK, 1 - cpol)
        if cpha:
            sample = _set_pin(sample, SPI_MOSI, request_bit)
            sample = _set_pin(sample, SPI_MISO, response_bit)
        samples.append(sample)

        sample = _set_pin(sample, SPI_CLOCK, cpol)
        if not cpha and index + 1 < 8:
            sample = _set_pin(sample, SPI_MOSI, request_bits[index + 1])
            sample = _set_pin(sample, SPI_MISO, response_bits[index + 1])
        samples.append(sample)

    sample = _set_pin(sample, SPI_SELECT_N, 1)
    samples.append(sample)
    order = "msb_first" if msb_first else "lsb_first"
    return BenchmarkCase(
        name=f"spi_mode{mode}_{order}",
        waveform=DigitalWaveform(4, tuple(samples)),
        truth=ProtocolTruth(
            family="SPI",
            parameters=(("mode", str(mode)), ("bit_order", order), ("word_bits", "8")),
            pin_roles=(
                ("clock", SPI_CLOCK),
                ("request_data", SPI_MOSI),
                ("response_data", SPI_MISO),
                ("select_n", SPI_SELECT_N),
            ),
            expected_input_symbols=(request,),
            expected_output_symbols=(response,),
        ),
    )


def decode_spi_reference(case: BenchmarkCase) -> tuple[int, int]:
    truth = case.truth
    mode = int(truth.parameter("mode"))
    cpol = mode >> 1
    cpha = mode & 1
    clock = truth.pin("clock")
    mosi = truth.pin("request_data")
    miso = truth.pin("response_data")
    select_n = truth.pin("select_n")
    request_bits: list[int] = []
    response_bits: list[int] = []
    previous = case.waveform.samples[0]

    for sample in case.waveform.samples[1:]:
        previous_clock = (previous >> clock) & 1
        clock_level = (sample >> clock) & 1
        selected = not ((sample >> select_n) & 1)
        leading = previous_clock == cpol and clock_level == 1 - cpol
        trailing = previous_clock == 1 - cpol and clock_level == cpol
        sampling_edge = trailing if cpha else leading
        if selected and sampling_edge:
            request_bits.append((sample >> mosi) & 1)
            response_bits.append((sample >> miso) & 1)
        previous = sample

    if len(request_bits) != 8 or len(response_bits) != 8:
        raise ValueError("SPI fixture did not contain one eight-bit word")
    msb_first = truth.parameter("bit_order") == "msb_first"

    def assemble(bits: list[int]) -> int:
        if msb_first:
            value = 0
            for bit in bits:
                value = (value << 1) | bit
            return value
        return sum(bit << index for index, bit in enumerate(bits))

    return assemble(request_bits), assemble(response_bits)


UART_DATA = 0


def make_uart_case(value: int, bit_ticks: int = 4) -> BenchmarkCase:
    if not 0 <= value <= 0xFF:
        raise ValueError("UART value must be a byte")
    if bit_ticks < 2:
        raise ValueError("bit_ticks must be at least two")
    levels = (1, 0, *((value >> bit) & 1 for bit in range(8)), 1, 1)
    samples = tuple(level for level in levels for _ in range(bit_ticks))
    return BenchmarkCase(
        name=f"uart_8n1_{value:02x}",
        waveform=DigitalWaveform(1, samples),
        truth=ProtocolTruth(
            family="UART",
            parameters=(
                ("data_bits", "8"),
                ("parity", "none"),
                ("stop_bits", "1"),
                ("bit_ticks", str(bit_ticks)),
                ("bit_order", "lsb_first"),
            ),
            pin_roles=(("request_data", UART_DATA),),
            expected_input_symbols=(value,),
        ),
    )


def decode_uart_reference(case: BenchmarkCase) -> int:
    samples = case.waveform.samples
    bit_ticks = int(case.truth.parameter("bit_ticks"))
    start = next(
        index
        for index in range(1, len(samples))
        if samples[index - 1] & 1 and not samples[index] & 1
    )
    if samples[start + bit_ticks // 2] & 1:
        raise ValueError("UART start bit is not low")
    value = 0
    for bit in range(8):
        sample_index = start + bit_ticks + bit * bit_ticks + bit_ticks // 2
        value |= (samples[sample_index] & 1) << bit
    stop_index = start + 9 * bit_ticks + bit_ticks // 2
    if not samples[stop_index] & 1:
        raise ValueError("UART stop bit is not high")
    return value


I2C_CLOCK = 0
I2C_DATA = 1


def make_i2c_write_case(address: int = 0x50, data: int = 0x2A) -> BenchmarkCase:
    if not 0 <= address < 0x80:
        raise ValueError("I2C address must be seven bits")
    if not 0 <= data <= 0xFF:
        raise ValueError("I2C data must be a byte")
    address_write = address << 1
    sample = (1 << I2C_CLOCK) | (1 << I2C_DATA)
    samples = [sample]
    sample = _set_pin(sample, I2C_DATA, 0)
    samples.append(sample)

    for byte in (address_write, data):
        for bit in _temporal_bits(byte, True):
            sample = _set_pin(sample, I2C_CLOCK, 0)
            sample = _set_pin(sample, I2C_DATA, bit)
            samples.append(sample)
            sample = _set_pin(sample, I2C_CLOCK, 1)
            samples.append(sample)
        sample = _set_pin(sample, I2C_CLOCK, 0)
        sample = _set_pin(sample, I2C_DATA, 0)
        samples.append(sample)
        sample = _set_pin(sample, I2C_CLOCK, 1)
        samples.append(sample)

    sample = _set_pin(sample, I2C_CLOCK, 0)
    sample = _set_pin(sample, I2C_DATA, 0)
    samples.append(sample)
    sample = _set_pin(sample, I2C_CLOCK, 1)
    samples.append(sample)
    sample = _set_pin(sample, I2C_DATA, 1)
    samples.append(sample)
    return BenchmarkCase(
        name="i2c_write_address50_data2a",
        waveform=DigitalWaveform(2, tuple(samples)),
        truth=ProtocolTruth(
            family="I2C",
            parameters=(("address_bits", "7"), ("direction", "write")),
            pin_roles=(("clock", I2C_CLOCK), ("bidirectional_data", I2C_DATA)),
            expected_input_symbols=(address_write, data),
            expected_ack_bits=(0, 0),
        ),
    )


def decode_i2c_reference(case: BenchmarkCase) -> tuple[tuple[int, ...], tuple[int, ...]]:
    clock = case.truth.pin("clock")
    data = case.truth.pin("bidirectional_data")
    samples = case.waveform.samples
    start = None
    stop = None
    sampled_bits: list[int] = []

    for index in range(1, len(samples)):
        previous = samples[index - 1]
        sample = samples[index]
        previous_clock = (previous >> clock) & 1
        clock_level = (sample >> clock) & 1
        previous_data = (previous >> data) & 1
        data_level = (sample >> data) & 1
        if previous_data == 1 and data_level == 0 and clock_level == 1:
            start = index
            continue
        if previous_data == 0 and data_level == 1 and clock_level == 1:
            stop = index
            continue
        if start is not None and stop is None and previous_clock == 0 and clock_level == 1:
            sampled_bits.append(data_level)

    if start is None or stop is None:
        raise ValueError("I2C fixture lacks start or stop")
    complete_groups = len(sampled_bits) // 9
    symbols: list[int] = []
    acknowledgements: list[int] = []
    for group in range(complete_groups):
        bits = sampled_bits[group * 9 : group * 9 + 9]
        value = 0
        for bit in bits[:8]:
            value = (value << 1) | bit
        symbols.append(value)
        acknowledgements.append(bits[8])
    return tuple(symbols), tuple(acknowledgements)


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    spi = tuple(
        make_spi_case(mode, msb_first)
        for mode in range(4)
        for msb_first in (True, False)
    )
    uart = tuple(make_uart_case(value) for value in (0x00, 0x55, 0xA5, 0xFF))
    return spi + uart + (make_i2c_write_case(),)
