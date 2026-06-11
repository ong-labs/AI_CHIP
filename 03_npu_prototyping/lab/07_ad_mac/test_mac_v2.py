"""cocotb testbench for mac_v2.v (advanced MAC).

기본 mac.v 의 cross_check 외에 추가 테스트:
  1. test_basic_accumulation     — 기능 정확성 (2-stage pipeline)
  2. test_enable_holds           — en=0 일 때 acc 유지
  3. test_clear_acc              — clear_acc 로 새 sequence 시작
  4. test_overflow_no_silent_wrap — INT32 누적이 비정상적으로 빠르게 overflow 안 됨
  5. test_valid_pipeline         — acc_valid 가 in_valid 를 2-cycle 지연으로 따라옴
  6. test_random_vs_numpy        — 100 INT8 pair, NumPy 와 cross-check

Pipeline latency: in_valid → 2 cycles → acc_valid (stage 1 곱 + stage 2 누적)
"""

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


def acc_int(dut) -> int:
    return dut.acc.value.to_signed()


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.en.value = 1
    dut.clear_acc.value = 0
    dut.in_data.value = 0
    dut.weight.value = 0
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def feed(dut, a: int, b: int, valid: int = 1, clear: int = 0):
    dut.in_data.value = a
    dut.weight.value = b
    dut.in_valid.value = valid
    dut.clear_acc.value = clear
    await RisingEdge(dut.clk)


async def drain_pipeline(dut, cycles: int = 3):
    """파이프라인 비우기 — in_valid=0 으로 N cycle 대기"""
    dut.in_data.value = 0
    dut.weight.value = 0
    dut.in_valid.value = 0
    dut.clear_acc.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_basic_accumulation(dut):
    """3 × 5 + 2 × 4 + 1 × 6 = 29"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    pairs = [(3, 5), (2, 4), (1, 6)]
    expected = sum(a * b for a, b in pairs)

    for a, b in pairs:
        await feed(dut, a, b, valid=1)
    await drain_pipeline(dut, 3)

    cocotb.log.info(f"basic: acc={acc_int(dut)}, expected={expected}")
    assert acc_int(dut) == expected
    assert int(dut.overflow.value) == 0


@cocotb.test()
async def test_enable_holds(dut):
    """en=0 일 때 acc 가 유지되어야 함"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    # 5*3 = 15 누적
    await feed(dut, 5, 3, valid=1)
    await drain_pipeline(dut, 3)
    acc_before = acc_int(dut)
    cocotb.log.info(f"before en=0: acc={acc_before}")
    assert acc_before == 15

    # en=0 + 가짜 입력 5 cycle
    dut.en.value = 0
    dut.in_data.value = 10
    dut.weight.value = 20
    dut.in_valid.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)

    acc_after = acc_int(dut)
    cocotb.log.info(f"after 5 cycles with en=0: acc={acc_after}")
    assert acc_after == acc_before, f"acc changed during en=0!"


@cocotb.test()
async def test_clear_acc(dut):
    """clear_acc 가 acc 를 리셋하고 그 cycle 의 product 부터 새로 누적"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    # 첫 시퀀스: 5*3 + 4*2 = 23
    await feed(dut, 5, 3, valid=1)
    await feed(dut, 4, 2, valid=1)
    await drain_pipeline(dut, 3)
    cocotb.log.info(f"first seq: acc={acc_int(dut)} (expect 23)")
    assert acc_int(dut) == 23

    # clear_acc 와 함께 새 시퀀스 시작: 7*8 = 56
    await feed(dut, 7, 8, valid=1, clear=1)
    await drain_pipeline(dut, 3)
    cocotb.log.info(f"after clear: acc={acc_int(dut)} (expect 56)")
    assert acc_int(dut) == 56


@cocotb.test()
async def test_no_silent_wrap(dut):
    """INT32 acc 가 100 × (127×127) 누적해도 silent wrap 없음.
    100 × 16129 = 1,612,900 → INT32 max(2,147,483,647) 보다 훨씬 작음 → overflow=0"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    for _ in range(100):
        await feed(dut, 127, 127, valid=1)
    await drain_pipeline(dut, 3)

    expected = 100 * 127 * 127
    cocotb.log.info(f"100 × (127×127) = {acc_int(dut)} (expect {expected})")
    assert acc_int(dut) == expected
    assert int(dut.overflow.value) == 0, "INT32 누적 범위 안인데 overflow flag 가 켜짐"


@cocotb.test()
async def test_valid_pipeline_propagation(dut):
    """in_valid 가 acc_valid 로 propagate 되며, 적절한 cycle 안에 도착해야 함.
    2-stage pipeline 이므로 ~2 cycle 지연 기대."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    assert int(dut.acc_valid.value) == 0, "reset 직후 acc_valid 는 0"

    # 한 cycle 동안만 valid input
    await feed(dut, 3, 5, valid=1)

    # 이후 invalid 로 두면서 acc_valid 가 *언제* 1 이 되는지 추적
    valid_cycle = None
    for cyc in range(1, 6):
        await feed(dut, 0, 0, valid=0)
        if int(dut.acc_valid.value) == 1 and valid_cycle is None:
            valid_cycle = cyc
            cocotb.log.info(f"acc_valid=1 at cycle {cyc} after in_valid pulse")

    # acc_valid 가 2~3 cycle 안에 와야 (2-stage pipeline)
    assert valid_cycle is not None, "acc_valid 가 5 cycle 안에 도착 안 함"
    assert 1 <= valid_cycle <= 3, f"기대 2-cycle 지연, 실제 {valid_cycle}"

    # 최종 acc 값 검증
    final_acc = acc_int(dut)
    cocotb.log.info(f"final acc={final_acc} (expect 15 = 3×5)")
    assert final_acc == 15


@cocotb.test()
async def test_random_vs_numpy(dut):
    """Random INT8 100쌍 — NumPy 와 cross-check"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    rng = np.random.default_rng(42)
    N = 100
    a = rng.integers(-50, 50, N, dtype=np.int8)
    b = rng.integers(-50, 50, N, dtype=np.int8)
    expected = int(np.dot(a.astype(np.int32), b.astype(np.int32)))

    for av, bv in zip(a, b):
        await feed(dut, int(av), int(bv), valid=1)
    await drain_pipeline(dut, 3)

    actual = acc_int(dut)
    cocotb.log.info(f"random 100 INT8: RTL={actual}, NumPy={expected}")
    assert actual == expected, f"mismatch: rtl={actual} numpy={expected}"
    assert int(dut.overflow.value) == 0
