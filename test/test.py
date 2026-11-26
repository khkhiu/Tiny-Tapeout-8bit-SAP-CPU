# SPDX-License-Identifier: Apache-2.0
# SAP style 8-bit CPU with external memory.
# A Python memory model stands in for the RP2040. Black-box only (pins, no
# internal signals) so the same tests run at gate level.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge

NOP, LDA, ADD, SUB, STA, LDI, JMP, JC, JZ, IN, OUT, HLT = (
    0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0xD, 0xE, 0xF)


def ins(op, arg=0):
    return (op << 4) | (arg & 0xF)


FIB_PROGRAM = [
    ins(LDI, 0), ins(STA, 14), ins(OUT), ins(LDI, 1), ins(STA, 15), ins(OUT),
    ins(ADD, 14), ins(JC, 0), ins(STA, 14), ins(OUT), ins(ADD, 15), ins(JC, 0),
    ins(STA, 15), ins(JMP, 5), 0x00, 0x00,
]
FIB_SEQUENCE = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]


class Memory:
    """What the RP2040 does: serve reads, capture writes and OUT, never fight the chip."""

    def __init__(self, dut, program):
        self.dut = dut
        self.mem = list(program) + [0] * (16 - len(program))
        self.outputs = []
        self.driving = False

    async def serve(self):
        dut = self.dut
        while True:
            await FallingEdge(dut.clk)
            uo = int(dut.uo_out.value)
            addr, we, out_stb = uo & 0xF, (uo >> 4) & 1, (uo >> 5) & 1
            oe = int(dut.uio_oe.value)
            assert oe in (0x00, 0xFF), f"partial uio_oe {oe:#x}"
            assert not (oe and self.driving), "bus contention: chip and memory both driving uio"

            if oe:  # chip is driving the bus this cycle
                data = int(dut.uio_out.value)
                if we:
                    self.mem[addr] = data
                if out_stb:
                    self.outputs.append(data)

            self.driving = not (we or out_stb)
            if self.driving:
                dut.uio_in.value = self.mem[addr]


def status(dut):
    uo = int(dut.uo_out.value)
    return {"halted": (uo >> 7) & 1, "fetch": (uo >> 6) & 1}


async def start(dut, program, ui=0):
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    mem = Memory(dut, program)
    dut.ena.value = 1
    dut.ui_in.value = ui
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    cocotb.start_soon(mem.serve())
    dut.rst_n.value = 1
    return mem


async def run_until_halt(dut, limit=2000):
    for _ in range(limit):
        await ClockCycles(dut.clk, 1)
        if status(dut)["halted"]:
            return
    raise AssertionError("CPU did not halt")


@cocotb.test()
async def test_fibonacci(dut):
    """Prints Fibonacci, wraps to 0 on overflow, keeps going."""
    mem = await start(dut, FIB_PROGRAM)
    await ClockCycles(dut.clk, 400)
    expected = FIB_SEQUENCE + FIB_SEQUENCE[:5]
    dut._log.info(f"OUT: {mem.outputs}")
    assert mem.outputs[:len(expected)] == expected
    assert not status(dut)["halted"]


@cocotb.test()
async def test_sub_jc_hlt(dut):
    """Count down from 10 by 3; halt when SUB borrows (C = 0)."""
    prog = [0] * 16
    prog[0:8] = [ins(LDA, 14), ins(OUT), ins(SUB, 15), ins(JC, 5), ins(HLT),
                 ins(STA, 13), ins(LDA, 13), ins(JMP, 1)]
    prog[14], prog[15] = 10, 3
    mem = await start(dut, prog)
    await run_until_halt(dut)
    assert mem.outputs == [10, 7, 4, 1]
    assert mem.mem[13] == 1, "STA did not write memory"
    n = len(mem.outputs)
    await ClockCycles(dut.clk, 50)
    assert status(dut)["halted"] and len(mem.outputs) == n


@cocotb.test()
async def test_jz(dut):
    """Count down to zero by 2 using JZ."""
    prog = [0] * 16
    prog[0:8] = [ins(LDA, 15), ins(OUT), ins(SUB, 14), ins(JZ, 6), ins(JMP, 1),
                 ins(NOP), ins(OUT), ins(HLT)]
    prog[14], prog[15] = 2, 6
    mem = await start(dut, prog)
    await run_until_halt(dut)
    assert mem.outputs == [6, 4, 2, 0]


@cocotb.test()
async def test_in_port(dut):
    """IN reads the switches on ui_in."""
    prog = [ins(IN), ins(OUT), ins(ADD, 15), ins(OUT), ins(HLT)] + [0] * 10 + [1]
    mem = await start(dut, prog, ui=0x41)
    await run_until_halt(dut)
    assert mem.outputs == [0x41, 0x42]


@cocotb.test()
async def test_cycle_counts(dut):
    """2 cycles per instruction, 3 for STA and OUT."""
    prog = [ins(NOP), ins(NOP), ins(STA, 15), ins(OUT), ins(HLT)] + [0] * 11
    await start(dut, prog)
    cycles = 0
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()  # sample after the flops have updated
        cycles += 1
        if status(dut)["halted"]:
            break
        assert cycles < 100
    assert cycles == 2 + 2 + 3 + 3 + 2, f"took {cycles} cycles"
