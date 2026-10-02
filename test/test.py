# SPDX-FileCopyrightText: © 2026 Damir Wallener
# SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

HOST_MODEL = Path(__file__).resolve().parents[1] / "experiments" / "minimum_mindreader"
sys.path.insert(0, str(HOST_MODEL))
from companion_controller import AsicSnapshot, DeckController  # noqa: E402
from companion_link import Command, ProductState, status_request  # noqa: E402


DISCOVER = int(Command.DISCOVER)
LEARN = int(Command.LEARN)
PROMOTE = int(Command.PROMOTE)
OWNERSHIP = int(Command.OWNERSHIP)
ACTIVATE = int(Command.ACTIVATE)

# Local SPI roles (clock, request, response, select) are deliberately scattered
# across the eight physical bidirectional pins.
SPI_PIN_MAP = (6, 1, 7, 4)


def remap_spi_sample(sample: int) -> int:
    result = 0
    for local_pin, physical_pin in enumerate(SPI_PIN_MAP):
        result |= ((sample >> local_pin) & 1) << physical_pin
    return result


def spi_mode1_frame(request: int, response: int) -> tuple[int, ...]:
    """Return an eight-pin waveform containing the bounded four-wire link."""
    sample = 1 << 3  # active-low select idle, clock idle low
    samples = [sample]
    sample &= ~(1 << 3)
    samples.append(sample)
    for bit in range(7, -1, -1):
        sample |= 1 << 0
        if (request >> bit) & 1:
            sample |= 1 << 1
        else:
            sample &= ~(1 << 1)
        if (response >> bit) & 1:
            sample |= 1 << 2
        else:
            sample &= ~(1 << 2)
        samples.append(sample)
        sample &= ~(1 << 0)
        samples.append(sample)
    samples.append(sample | (1 << 3))
    return tuple(remap_spi_sample(sample) for sample in samples)


def learned_response(request: int) -> int:
    return 0x60 | (request & 0x03)


def uart_frame(value: int, physical_pin: int, bit_ticks: int = 4) -> tuple[int, ...]:
    levels = (1, 0, *((value >> bit) & 1 for bit in range(8)), 1, 1)
    return tuple((level << physical_pin) for level in levels for _ in range(bit_ticks))


def i2c_write_frame(
    address: int = 0x50,
    data: int = 0x2A,
    clock_pin: int = 2,
    data_pin: int = 5,
) -> tuple[int, ...]:
    sample = (1 << clock_pin) | (1 << data_pin)
    samples = [sample, sample & ~(1 << data_pin)]
    sample = samples[-1]
    for value in (address << 1, data):
        for bit in range(7, -1, -1):
            sample &= ~(1 << clock_pin)
            if (value >> bit) & 1:
                sample |= 1 << data_pin
            else:
                sample &= ~(1 << data_pin)
            samples.append(sample)
            sample |= 1 << clock_pin
            samples.append(sample)
        sample &= ~(1 << clock_pin)
        sample &= ~(1 << data_pin)
        samples.append(sample)
        sample |= 1 << clock_pin
        samples.append(sample)
    sample &= ~(1 << clock_pin)
    sample &= ~(1 << data_pin)
    samples.append(sample)
    sample |= 1 << clock_pin
    samples.append(sample)
    sample |= 1 << data_pin
    samples.append(sample)
    return tuple(samples)


async def tick(dut, cycles: int = 1) -> None:
    await ClockCycles(dut.clk, cycles)
    await Timer(1, unit="ns")


async def drive_samples(dut, samples: tuple[int, ...], hold_cycles: int = 2) -> None:
    for sample in samples:
        dut.uio_in.value = sample
        await tick(dut, hold_cycles)


@cocotb.test()
async def test_autonomous_mindreader_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    spi_idle = remap_spi_sample(0x08)
    response_pin = SPI_PIN_MAP[2]
    response_mask = 1 << response_pin
    dut.uio_in.value = spi_idle
    dut.rst_n.value = 0
    await tick(dut, 2)
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uo_out.value) == 0

    dut.rst_n.value = 1
    await tick(dut)

    # ui[0] selects the companion-MCU bank during a passive status read.
    # Its identity and version give firmware a stable discovery handshake.
    dut.ui_in.value = status_request(0, companion=True)
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x4D
    dut.ui_in.value = status_request(1, companion=True)
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x52
    dut.ui_in.value = status_request(2, companion=True)
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x01
    dut.ui_in.value = 0
    await tick(dut)

    # Quiet is an all-eight-pin claim. Activity on a pin outside the current
    # four-wire SPI link must reset the quiet interval without ever driving.
    await tick(dut, 65)
    assert int(dut.uo_out.value) & (1 << 4)
    dut.uio_in.value = spi_idle | (1 << 5)
    await tick(dut)
    assert not (int(dut.uo_out.value) & (1 << 4))
    assert int(dut.uio_oe.value) == 0
    dut.uio_in.value = spi_idle
    await tick(dut)

    # One passive frame identifies select, clock, sampling edge, and data pins.
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, spi_mode1_frame(0xA0, 0x60))
    dut.ui_in.value = 0
    await tick(dut, 2)
    assert int(dut.uo_out.value) & 0x01
    assert int(dut.uio_oe.value) == 0

    # Passive status pages expose the shared taxonomy evidence. The scattered
    # SPI frame activated exactly pins 1, 4, 6, and 7; it retains both a
    # single-wire interpretation and a selected synchronous interpretation.
    dut.ui_in.value = 0x80
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == sum(1 << pin for pin in SPI_PIN_MAP)
    dut.ui_in.value = 0xC0
    await Timer(1, unit="ns")
    structural = int(dut.uo_out.value)
    assert structural & 0x80, f"expected retained ambiguity: 0x{structural:02x}"
    assert not (structural & 0x40), f"unexpected insufficiency: 0x{structural:02x}"
    assert structural & 0x10, f"router not ready: 0x{structural:02x}"
    assert structural & 0x01, f"async route missing: 0x{structural:02x}"
    assert structural & 0x02, f"selected-clock route missing: 0x{structural:02x}"
    assert not (structural & 0x04), f"false two-wire route: 0x{structural:02x}"
    dut.ui_in.value = 0xE0
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == (1 << SPI_PIN_MAP[0])
    dut.ui_in.value = 0
    await tick(dut)

    # Eight observations resolve the lossy request->response direction and
    # simultaneously establish an admissible external timing envelope.
    dut.ui_in.value = LEARN
    for request in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA8, 0xAF):
        await drive_samples(dut, spi_mode1_frame(request, learned_response(request)))
    dut.ui_in.value = 0
    await tick(dut, 2)
    status = int(dut.uo_out.value)
    assert status & (1 << 1), f"direction unresolved: status=0x{status:02x}"
    assert status & (1 << 5), f"timing inadmissible: status=0x{status:02x}"
    assert int(dut.uio_oe.value) == 0

    # Promotion without electrical ownership is rejected and remains passive.
    dut.ui_in.value = PROMOTE
    await tick(dut)
    assert int(dut.uo_out.value) & (1 << 7)
    assert not (int(dut.uo_out.value) & (1 << 2))
    assert int(dut.uio_oe.value) == 0

    # The product controller uses explicit capability bits, not a pretty-state
    # guess, to promote and activate the model.
    deck = DeckController()
    dut.ui_in.value = deck.command(
        AsicSnapshot(ProductState.AMBIGUOUS, int(dut.uo_out.value)),
        listen_pressed=False, jack_pressed=True, active_switch=True,
    )
    await tick(dut)
    dut.ui_in.value = deck.command(
        AsicSnapshot(ProductState.MODEL_READY, int(dut.uo_out.value)),
        listen_pressed=False, jack_pressed=False, active_switch=True,
    )
    await tick(dut, 2)
    assert int(dut.uo_out.value) & (1 << 2)
    dut.ui_in.value = deck.command(
        AsicSnapshot(ProductState.MODEL_READY, int(dut.uo_out.value)),
        listen_pressed=False, jack_pressed=True, active_switch=True,
    )
    await tick(dut)
    assert int(dut.uo_out.value) & (1 << 3)
    dut.ui_in.value = deck.command(
        AsicSnapshot(ProductState.EMULATING, int(dut.uo_out.value)),
        listen_pressed=False, jack_pressed=False, active_switch=True,
    )

    # The ninth request was never observed. The learned model must emit 0x63
    # on the inferred response pin while all other bidirectional pins stay Z.
    held_out = spi_mode1_frame(0xA7, 0x63)
    previous = held_out[0]
    sampled_bits = 0
    for sample_index, sample in enumerate(held_out):
        # Model physical pad loopback: the external stimulus owns select,
        # clock, and request, while the response input path reflects uio_out.
        base = sample & ~response_mask
        dut.uio_in.value = base | (int(dut.uio_out.value) & response_mask)
        await Timer(1, unit="ns")
        response_bit = (int(dut.uio_out.value) >> response_pin) & 1
        dut.uio_in.value = base | (response_bit << response_pin)
        await Timer(1, unit="ns")

        selected = not ((sample >> SPI_PIN_MAP[3]) & 1)
        trailing_sample = (
            sample_index > 0
            and selected
            and ((previous >> SPI_PIN_MAP[0]) & 1) == 1
            and ((sample >> SPI_PIN_MAP[0]) & 1) == 0
        )
        if trailing_sample:
            expected_bit = (0x63 >> (7 - sampled_bits)) & 1
            assert response_bit == expected_bit
            sampled_bits += 1

        for _ in range(2):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            response_bit = (int(dut.uio_out.value) >> response_pin) & 1
            dut.uio_in.value = base | (response_bit << response_pin)
            await Timer(1, unit="ns")
            assert int(dut.uio_oe.value) == (response_mask if selected else 0)
        previous = sample
    assert sampled_bits == 8

    # Pad-loopback disagreement removes output enable immediately, then latches
    # a fault. This deliberately drives the observed response opposite the
    # model's first response bit on a new selected frame.
    dut.uio_in.value = response_mask
    await Timer(1, unit="ns")
    assert int(dut.uio_oe.value) == 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) & (1 << 6)
    assert not (int(dut.uo_out.value) & (1 << 3))

    # TinyTapeout disable remains a combinational authority boundary.
    dut.ena.value = 0
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def test_uart_symbol_hypothesis_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    uart_pin = 3
    samples = uart_frame(0x55, uart_pin)
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = samples[0]
    dut.rst_n.value = 0
    await tick(dut, 2)
    dut.rst_n.value = 1
    await tick(dut)

    dut.ui_in.value = DISCOVER
    await drive_samples(dut, samples, hold_cycles=1)
    dut.ui_in.value = 0
    for _ in range(500):
        await tick(dut)
        # Page 5 exposes the UART evaluator's ready bit.
        dut.ui_in.value = 0xA4
        await Timer(1, unit="ns")
        if int(dut.uo_out.value) & 0x80:
            break
        dut.ui_in.value = 0
    else:
        assert False, "UART hypothesis evaluator did not finish"
    assert int(dut.uio_oe.value) == 0

    dut.ui_in.value = 0
    await Timer(1, unit="ns")
    assert not (int(dut.uo_out.value) & 0x01), "UART must not masquerade as SPI"

    # UART page 5: ready, valid, ambiguity, pin-valid, idle, and physical pin.
    dut.ui_in.value = 0xA4
    await Timer(1, unit="ns")
    metadata = int(dut.uo_out.value)
    assert metadata & 0x80
    assert metadata & 0x40
    assert metadata & 0x10
    assert metadata & 0x08
    assert (metadata & 0x07) == uart_pin

    # Page 6 contains period candidates 2..9; period four is bit two.
    dut.ui_in.value = 0xC4
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) & (1 << 2)

    # Page 8 contains widths 5..9; width eight is bit three.
    dut.ui_in.value = 0x88
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) & (1 << 3)

    # Page 9 exposes parity and stop compatibility. None and one-stop survive.
    dut.ui_in.value = 0xA8
    await Timer(1, unit="ns")
    framing = int(dut.uo_out.value)
    assert framing & (1 << 2)
    assert framing & (1 << 0)
    assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def test_i2c_symbol_hypothesis_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    clock_pin = 2
    data_pin = 5
    samples = i2c_write_frame(clock_pin=clock_pin, data_pin=data_pin)
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = samples[0]
    dut.rst_n.value = 0
    await tick(dut, 2)
    dut.rst_n.value = 1
    await tick(dut)

    dut.ui_in.value = DISCOVER
    await drive_samples(dut, samples, hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    assert not (int(dut.uo_out.value) & 0x01), "I2C must not masquerade as SPI"
    assert int(dut.uio_oe.value) == 0

    dut.ui_in.value = 0xAC
    await Timer(1, unit="ns")
    metadata = int(dut.uo_out.value)
    assert metadata & 0x80
    assert metadata & 0x40
    assert not (metadata & 0x20)
    assert (metadata & 0x1F) == 1

    dut.ui_in.value = 0xCC
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == (1 << clock_pin)
    dut.ui_in.value = 0xEC
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == (1 << data_pin)
    assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def test_generic_event_framer_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await tick(dut, 2)
    dut.rst_n.value = 1
    await tick(dut)

    # Two equal four-transition bursts with a five-clock quiet gap.
    samples = (0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0)
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, samples, hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    assert int(dut.uio_oe.value) == 0

    dut.ui_in.value = 0x82
    await Timer(1, unit="ns")
    metadata = int(dut.uo_out.value)
    assert metadata & 0x80
    assert metadata & 0x40
    assert not (metadata & 0x20)
    assert ((metadata >> 3) & 0x03) == 2
    assert (metadata & 0x07) == 0b110

    dut.ui_in.value = 0xA2
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0
    dut.ui_in.value = 0xC2
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 4
    dut.ui_in.value = 0xE2
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 4
    assert int(dut.uio_oe.value) == 0

    # The UART evaluator finishes later than the online engines. Once every
    # inference surface is ready, the merged report must retain both generic
    # explanations rather than manufacture a protocol name.
    for _ in range(500):
        dut.ui_in.value = 0xA6
        await tick(dut)
        if int(dut.uo_out.value) & 0x80:
            break
    else:
        assert False, "equivalence classifier did not become ready"
    equivalence = int(dut.uo_out.value)
    assert equivalence & 0x40
    assert not (equivalence & 0x20)
    assert not (equivalence & 0x10)
    assert (equivalence & 0x0F) == 2

    dut.ui_in.value = 0x86
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0b110000
    assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def test_passive_refusal_controls_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    async def reset_with(initial_sample: int) -> None:
        dut.ena.value = 1
        dut.ui_in.value = 0
        dut.uio_in.value = initial_sample
        dut.rst_n.value = 0
        await tick(dut, 2)
        dut.rst_n.value = 1
        await tick(dut)

    # Silence completes every passive observation surface but supports no
    # interpretation. That is insufficiency, never permission to drive.
    await reset_with(0)
    dut.ui_in.value = DISCOVER
    await tick(dut, 20)
    dut.ui_in.value = 0
    await tick(dut, 2)
    dut.ui_in.value = 0xA6
    await Timer(1, unit="ns")
    report = int(dut.uo_out.value)
    assert report & 0x80
    assert report & 0x10
    assert (report & 0x0F) == 0
    dut.ui_in.value = 0x86
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0
    assert int(dut.uio_oe.value) == 0
    # A selected-synchronous fragment without its closing select edge cannot
    # complete physical inference.
    fragment = spi_mode1_frame(0xA5, 0x62)[:8]
    await reset_with(fragment[0])
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, fragment, hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    assert not (int(dut.uo_out.value) & 0x01)
    assert int(dut.uio_oe.value) == 0

    # UART-like timing contaminated by a second active pin refuses pin identity.
    uart_samples = list(uart_frame(0x55, 3))
    for index in range(len(uart_samples) // 2, len(uart_samples)):
        uart_samples[index] |= (index & 1) << 5
    await reset_with(uart_samples[0])
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, tuple(uart_samples), hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    dut.ui_in.value = 0xA4
    await Timer(1, unit="ns")
    uart_metadata = int(dut.uo_out.value)
    assert uart_metadata & 0x80
    assert not (uart_metadata & 0x40)
    assert not (uart_metadata & 0x10)
    assert int(dut.uio_oe.value) == 0

    # A coherent two-wire transfer without STOP is not a valid framed result.
    truncated_i2c = i2c_write_frame()[:-1]
    await reset_with(truncated_i2c[0])
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, truncated_i2c, hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    dut.ui_in.value = 0xAC
    await Timer(1, unit="ns")
    i2c_metadata = int(dut.uo_out.value)
    assert i2c_metadata & 0x80
    assert not (i2c_metadata & 0x40)
    assert (i2c_metadata & 0x1F) == 0
    assert int(dut.uio_oe.value) == 0

    # Unequal quiet-gap-separated bursts retain gap framing but eliminate the
    # equal-event-count explanation.
    unequal = (0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0)
    await reset_with(0)
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, unequal, hold_cycles=1)
    dut.ui_in.value = 0
    await tick(dut, 2)
    dut.ui_in.value = 0x82
    await Timer(1, unit="ns")
    generic_metadata = int(dut.uo_out.value)
    assert generic_metadata & 0x02
    assert not (generic_metadata & 0x04)
    assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def test_observation_integrity_disclosure_top(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await tick(dut, 2)
    dut.rst_n.value = 1
    await tick(dut)

    # More transitions than the bounded counters can represent must poison
    # the report explicitly, never silently produce a confident conclusion.
    dut.ui_in.value = DISCOVER
    for index in range(260):
        dut.uio_in.value = index & 1
        await tick(dut)
    dut.ui_in.value = 0
    await tick(dut, 2)

    # Pages 16/17/18 report compromised/saturated/recapture.
    dut.ui_in.value = 0xC6
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x06
    dut.ui_in.value = 0xE6
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x06
    dut.ui_in.value = 0x8A
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0x06

    # Integrity detail: aggregate saturation plus router, generic-framing,
    # and physical-role collectors disclose that their bounds were exceeded.
    dut.ui_in.value = 0xEA
    await Timer(1, unit="ns")
    integrity = int(dut.uo_out.value)
    assert integrity & (1 << 6)
    assert integrity & (1 << 5)
    assert integrity & (1 << 2)
    assert integrity & (1 << 1)
    assert int(dut.uio_oe.value) == 0
