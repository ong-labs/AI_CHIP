"""cocotb testbench for the Verilog MAC.

Tests:
  1. basic — simple dot product against ground truth
  2. signed — negative values handled correctly
  3. no_overflow_with_int32 — 1000 × (1 × 1) accumulates to 1000
  4. cross_check_python — random INT8 vectors compared against Python MAC class
"""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

# Import Python MACUnit from week3/reference/02_mac_and_memory.py
_spec = spec_from_file_location(
    "npu_mac_mem",
    str(Path(__file__).parent.parent / "02_hardware_comp_bench.py"),
)
_mod = module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MACUnit = _mod.MACUnit


def acc_int(dut) -> int:
    return dut.acc.value.to_signed()


async def reset_dut(dut):
    dut.rst.value = 1
    dut.in_data.value = 0
    dut.weight.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def feed_pair(dut, a: int, b: int) -> int:
    dut.in_data.value = a
    dut.weight.value = b
    await RisingEdge(dut.clk)
    return acc_int(dut)


@cocotb.test()
async def test_basic(dut):
    """3 × 5 + 2 × 4 + 1 × 6 = 29"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    expected = 0
    for a, b in [(3, 5), (2, 4), (1, 6)]:
        await feed_pair(dut, a, b)
        expected += a * b
    dut.in_data.value = 0
    dut.weight.value = 0
    await RisingEdge(dut.clk)
    actual = acc_int(dut)
    cocotb.log.info(f"acc={actual} expected={expected}")
    assert actual == expected


@cocotb.test()
async def test_signed(dut):
    """negative weights and inputs"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    pairs = [(-3, 5), (4, -7), (-2, -8), (10, 12)]
    expected = sum(a * b for a, b in pairs)
    for a, b in pairs:
        await feed_pair(dut, a, b)
    dut.in_data.value = 0
    dut.weight.value = 0
    await RisingEdge(dut.clk)
    actual = acc_int(dut)
    cocotb.log.info(f"signed: acc={actual} expected={expected}")
    assert actual == expected


@cocotb.test()
async def test_no_overflow_with_int32(dut):
    """1000 × (1 × 1) = 1000. With INT32 accum this stays correct.
    The Python reference 02_mac_and_memory.py demonstrates the INT8-accum failure."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    for _ in range(1000):
        await feed_pair(dut, 1, 1)
    dut.in_data.value = 0
    dut.weight.value = 0
    await RisingEdge(dut.clk)
    actual = acc_int(dut)
    assert actual == 1000, f"INT32 accum should give 1000, got {actual}"


@cocotb.test()
async def test_cross_check_python(dut):
    """Random INT8 vectors — compare Verilog MAC with Python MACUnit (int8 in, int32 acc)."""
    rng = np.random.default_rng(42)
    N = 100
    a = rng.integers(-50, 50, N, dtype=np.int8)
    b = rng.integers(-50, 50, N, dtype=np.int8)

    py_mac = MACUnit("int8", "int8", "int32")
    py_expected = []
    for av, bv in zip(a, b):
        py_mac.step(int(av), int(bv))
        py_expected.append(int(py_mac.output))

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    for av, bv in zip(a, b):
        await feed_pair(dut, int(av), int(bv))

    dut.in_data.value = 0
    dut.weight.value = 0
    await RisingEdge(dut.clk)
    rtl_final = acc_int(dut)
    py_final = py_expected[-1]

    cocotb.log.info(f"Final  RTL={rtl_final}  Python={py_final}")
    assert rtl_final == py_final, f"final mismatch: rtl={rtl_final} python={py_final}"
    cocotb.log.info(f"Cross-check passed on {N} INT8 pairs")
