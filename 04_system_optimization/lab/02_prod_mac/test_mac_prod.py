"""cocotb testbench for mac_prod.v (production-style systolic MAC cell).

TPU 셀 동작:
  - weight 한 번 로드 후 stationary (weight_reg)
  - activation 옆으로 흘림 : act_in(t) → act_out(t+1)
  - partial sum 아래로 흘림 : psum_out(t+1) = psum_in(t) + act_in(t) × weight_reg

Tests:
  1. test_weight_load_and_mac   — weight 로드 후 단일 곱
  2. test_weight_stationary     — weight 1회 로드, activation 여러 번
  3. test_act_propagation       — act_in 이 1 cycle 후 act_out 으로
  4. test_psum_chain            — psum_out → psum_in feedback 으로 누적
  5. test_enable_holds          — en=0 동안 모든 reg 동결
  6. test_random_vs_numpy       — 100 INT8, NumPy dot 와 일치

cocotb 2.x 노트: RisingEdge 는 NBA 적용 *전* 에 리턴되므로,
post-edge 값을 읽으려면 ReadOnly 까지 진행해야 함.
헬퍼 `tick()` 가 그 boilerplate 를 캡슐화.
"""
import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep


def psum(dut) -> int:
    return dut.psum_out.value.to_signed()


def act_out(dut) -> int:
    return dut.act_out.value.to_signed()


async def tick(dut):
    """한 cycle 진행 + NBA settle 까지 대기 (post-edge 값 읽기 가능)"""
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()   # ReadWrite 로 돌아와 다음 사이클 write 가능


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.en.value = 1
    dut.load_weight.value = 0
    dut.weight_in.value = 0
    dut.act_in.value = 0
    dut.psum_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await tick(dut)


async def load_weight(dut, w: int):
    """1 cycle strobe 로 weight_reg 에 w 적재"""
    dut.load_weight.value = 1
    dut.weight_in.value = w
    await tick(dut)
    dut.load_weight.value = 0
    dut.weight_in.value = 0


@cocotb.test()
async def test_weight_load_and_mac(dut):
    """weight=3 로드 후 act=5 → psum_out = 0 + 5×3 = 15"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    await load_weight(dut, 3)

    dut.act_in.value = 5
    dut.psum_in.value = 0
    await tick(dut)

    cocotb.log.info(f"psum_out={psum(dut)} (expect 15)")
    assert psum(dut) == 15


@cocotb.test()
async def test_weight_stationary(dut):
    """weight=4 1회 로드, activation 여러 개 — 모두 같은 weight 와 곱"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    await load_weight(dut, 4)

    for a in [1, 2, 3, 5, 7]:
        dut.act_in.value = a
        dut.psum_in.value = 0
        await tick(dut)
        cocotb.log.info(f"act={a} → psum_out={psum(dut)} (expect {a*4})")
        assert psum(dut) == a * 4


@cocotb.test()
async def test_act_propagation(dut):
    """act_in 이 정확히 1 cycle 후 act_out 으로 나옴"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    await load_weight(dut, 1)

    dut.psum_in.value = 0
    for a in [7, -3, 11, 25, -50]:
        dut.act_in.value = a
        await tick(dut)
        cocotb.log.info(f"act_in={a}, act_out={act_out(dut)}")
        assert act_out(dut) == a


@cocotb.test()
async def test_psum_chain(dut):
    """psum_out → psum_in feedback 으로 누적 (systolic column 모사)"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    await load_weight(dut, 2)

    acts = [3, 5, 7, 11]
    expected = 0
    dut.psum_in.value = 0
    for a in acts:
        dut.act_in.value = a
        await tick(dut)
        expected += a * 2
        cocotb.log.info(f"a={a} → psum_out={psum(dut)} (expect {expected})")
        assert psum(dut) == expected
        dut.psum_in.value = psum(dut)


@cocotb.test()
async def test_enable_holds(dut):
    """en=0 5 cycle 동안 모든 reg 가 정지"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    await load_weight(dut, 3)

    dut.act_in.value = 5
    dut.psum_in.value = 0
    await tick(dut)
    psum_held = psum(dut)
    assert psum_held == 15

    dut.en.value = 0
    dut.act_in.value = 100
    dut.psum_in.value = 999
    for _ in range(5):
        await tick(dut)

    cocotb.log.info(f"en=0 5 cycles: psum_out={psum(dut)} (held at {psum_held})")
    assert psum(dut) == psum_held


@cocotb.test()
async def test_random_vs_numpy(dut):
    """Fixed weight × 100 random INT8 activations → NumPy 일치"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    W = 7
    await load_weight(dut, W)

    rng = np.random.default_rng(42)
    N = 100
    acts = rng.integers(-50, 50, N, dtype=np.int8)
    expected = int(np.sum(acts.astype(np.int32)) * W)

    dut.psum_in.value = 0
    running = 0
    for a in acts:
        dut.act_in.value = int(a)
        await tick(dut)
        running += int(a) * W
        assert psum(dut) == running, f"mismatch at a={a}: rtl={psum(dut)} py={running}"
        dut.psum_in.value = psum(dut)

    cocotb.log.info(f"100 acts × W={W}: psum_out={psum(dut)}, NumPy={expected}")
    assert psum(dut) == expected
