# SPDX-FileCopyrightText: © 2026 Damir Wallener
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


DISCOVER = 1 << 0
LEARN = 1 << 1
PROMOTE = 1 << 2
OWNERSHIP = 1 << 3
ACTIVATE = 1 << 4


def spi_mode1_frame(request: int, response: int) -> tuple[int, ...]:
    """Return the four-pin waveform used by the bounded autonomous learner."""
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
    return tuple(samples)


def learned_response(request: int) -> int:
    return 0x60 | (request & 0x03)


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
    dut.uio_in.value = 0x08
    dut.rst_n.value = 0
    await tick(dut, 2)
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uo_out.value) == 0

    dut.rst_n.value = 1
    await tick(dut)

    # One passive frame identifies select, clock, sampling edge, and data pins.
    dut.ui_in.value = DISCOVER
    await drive_samples(dut, spi_mode1_frame(0xA0, 0x60))
    dut.ui_in.value = 0
    await tick(dut, 2)
    assert int(dut.uo_out.value) & 0x01
    assert int(dut.uio_oe.value) == 0

    # Eight observations resolve the lossy request->response direction and
    # simultaneously establish an admissible external timing envelope.
    dut.ui_in.value = LEARN
    for request in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA8, 0xAF):
        await drive_samples(dut, spi_mode1_frame(request, learned_response(request)))
    dut.ui_in.value = 0
    await tick(dut, 2)
    status = int(dut.uo_out.value)
    assert status & (1 << 1), f"direction unresolved: status=0x{status:02x}"
    assert status & (1 << 4), f"timing unobserved: status=0x{status:02x}"
    assert status & (1 << 5), f"timing inadmissible: status=0x{status:02x}"
    assert int(dut.uio_oe.value) == 0

    # Promotion without electrical ownership is rejected and remains passive.
    dut.ui_in.value = PROMOTE
    await tick(dut)
    assert int(dut.uo_out.value) & (1 << 7)
    assert not (int(dut.uo_out.value) & (1 << 2))
    assert int(dut.uio_oe.value) == 0

    # Authorized promotion freezes the learned model; activation is separate.
    dut.ui_in.value = OWNERSHIP | PROMOTE
    await tick(dut)
    dut.ui_in.value = OWNERSHIP
    await tick(dut, 2)
    assert int(dut.uo_out.value) & (1 << 2)
    dut.ui_in.value = OWNERSHIP | ACTIVATE
    await tick(dut)
    assert int(dut.uo_out.value) & (1 << 3)

    # The ninth request was never observed. The learned model must emit 0x63
    # on the inferred response pin while all other bidirectional pins stay Z.
    held_out = spi_mode1_frame(0xA7, 0x63)
    previous = held_out[0]
    sampled_bits = 0
    for sample_index, sample in enumerate(held_out):
        # Model physical pad loopback: the external stimulus owns select,
        # clock, and request, while the response input path reflects uio_out.
        base = sample & ~(1 << 2)
        dut.uio_in.value = base | (((int(dut.uio_out.value) >> 2) & 1) << 2)
        await Timer(1, unit="ns")
        response_bit = (int(dut.uio_out.value) >> 2) & 1
        dut.uio_in.value = base | (response_bit << 2)
        await Timer(1, unit="ns")

        selected = not ((sample >> 3) & 1)
        trailing_sample = (
            sample_index > 0
            and selected
            and ((previous >> 0) & 1) == 1
            and ((sample >> 0) & 1) == 0
        )
        if trailing_sample:
            expected_bit = (0x63 >> (7 - sampled_bits)) & 1
            assert response_bit == expected_bit
            sampled_bits += 1

        for _ in range(2):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            response_bit = (int(dut.uio_out.value) >> 2) & 1
            dut.uio_in.value = base | (response_bit << 2)
            await Timer(1, unit="ns")
            assert int(dut.uio_oe.value) == (0x04 if selected else 0)
        previous = sample
    assert sampled_bits == 8

    # Pad-loopback disagreement removes output enable immediately, then latches
    # a fault. This deliberately drives the observed response opposite the
    # model's first response bit on a new selected frame.
    dut.uio_in.value = 0x04
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
