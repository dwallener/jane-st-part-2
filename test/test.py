# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


@cocotb.test()
async def test_project(dut):
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0xA5
    dut.uio_in.value = 0x10
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await Timer(1, unit="ns")

    assert int(dut.uo_out.value) == 0xA5
    assert int(dut.uio_out.value) == 0x10
    assert int(dut.uio_oe.value) == 0x0F

    dut.rst_n.value = 1

    for count in range(1, 5):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        assert int(dut.uo_out.value) == (count ^ 0xA5)
        assert int(dut.uio_out.value) == (count + 0x10)
        assert int(dut.uio_oe.value) == 0x0F

    # Tiny Tapeout enable must force every externally driven path safe without
    # waiting for another clock edge.
    dut.ena.value = 0
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0
