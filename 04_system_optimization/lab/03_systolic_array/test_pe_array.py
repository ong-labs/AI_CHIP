"""test_pe_array.py — pe_array (skew/loader 없는 순수 격자) 검증.

전략:
  - testbench 가 weight 를 직접 driver (load_weight_flat=all 1, 1 cycle pulse)
  - testbench 가 act_left_flat 에 *manual skew* 적용해서 입력
  - psum_bot_flat 을 매 cycle 캡처, C[m][j] = psum_bot[j] at cycle (m+j+R-1)

기본 인스턴스: ROWS=4, COLS=4, DATA_WIDTH=8, ACC_WIDTH=32 (pe_array.v default)
"""
import cocotb
import numpy as np
from cocotb.clock import Clock

from cocotb_helpers import tick, reset_active_low, pack_flat, read_signed_vec


R, C, DW, AW = 4, 4, 8, 32


async def init_signals(dut):
    dut.en.value = 1
    dut.load_weight_flat.value = 0
    dut.weight_in_flat.value = 0
    dut.act_left_flat.value = 0
    dut.psum_top_flat.value = 0


async def load_weights(dut, B):
    """B (R×C int list) 를 1 cycle 만에 모든 PE 에 로드"""
    flat = pack_flat([B[i][j] for i in range(R) for j in range(C)], DW)
    dut.load_weight_flat.value = (1 << (R * C)) - 1
    dut.weight_in_flat.value = flat
    await tick(dut)
    dut.load_weight_flat.value = 0
    dut.weight_in_flat.value = 0


def build_skewed_streams(A):
    """A (M×R) → R 개 stream, row k 는 k cycle 지연.
    리턴 streams[k][cyc], 길이 M+R-1"""
    M = len(A)
    L = M + R - 1
    streams = [[0] * L for _ in range(R)]
    for k in range(R):
        for m in range(M):
            streams[k][k + m] = A[m][k]
    return streams


async def stream_and_collect(dut, A):
    """skewed activation 흘리고 psum_bot 캡처 → C[m][j] 추출"""
    M = len(A)
    streams = build_skewed_streams(A)
    L = len(streams[0])
    drain = R + C

    history = []
    for cyc in range(L + drain):
        act_vec = [streams[k][cyc] if cyc < L else 0 for k in range(R)]
        dut.act_left_flat.value = pack_flat(act_vec, DW)
        await tick(dut)
        psum_vec = read_signed_vec(dut.psum_bot_flat, C, AW)
        history.append(psum_vec)

    # C[m][j] = history[m + j + R - 1][j]
    actual = [[history[m + j + R - 1][j] for j in range(C)] for m in range(M)]
    return actual, history


@cocotb.test()
async def test_identity_weight(dut):
    """B = I (단위행렬) → C = A (입력 그대로)"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    B = [[1 if i == j else 0 for j in range(C)] for i in range(R)]
    A = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
    expected = (np.array(A) @ np.array(B)).tolist()

    await load_weights(dut, B)
    actual, _ = await stream_and_collect(dut, A)

    cocotb.log.info(f"actual={actual}")
    cocotb.log.info(f"expected={expected}")
    assert actual == expected


@cocotb.test()
async def test_4x4_random(dut):
    """4×4 weight + 6×4 activation, NumPy 와 일치"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    rng = np.random.default_rng(0)
    B = rng.integers(-8, 8, (R, C)).tolist()
    A = rng.integers(-8, 8, (6, R)).tolist()
    expected = (np.array(A) @ np.array(B)).tolist()

    await load_weights(dut, B)
    actual, _ = await stream_and_collect(dut, A)

    cocotb.log.info(f"B={B}")
    cocotb.log.info(f"A={A}")
    cocotb.log.info(f"actual={actual}")
    cocotb.log.info(f"expected={expected}")
    assert actual == expected


@cocotb.test()
async def test_4x4_negative(dut):
    """음수 weight + 음수 activation"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    rng = np.random.default_rng(42)
    B = rng.integers(-50, 0, (R, C)).tolist()
    A = rng.integers(-50, 0, (4, R)).tolist()
    expected = (np.array(A) @ np.array(B)).tolist()

    await load_weights(dut, B)
    actual, _ = await stream_and_collect(dut, A)

    cocotb.log.info(f"actual={actual}")
    cocotb.log.info(f"expected={expected}")
    assert actual == expected
