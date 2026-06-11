"""test_systolic_top.py — 5개 서브모듈이 통합되어 동작하는지 end-to-end 검증.

전략:
  - weight_loader 로 weight 한 번 로드 (1 cycle start 펄스)
  - input_skew 가 내부에서 자동 skew → testbench 는 parallel activation 만 입력
  - output_collect 가 결과 캡처
  - NumPy 와 cross-check
"""
import cocotb
import numpy as np
from cocotb.clock import Clock

from cocotb_helpers import tick, reset_active_low, pack_flat, read_signed_vec


R, C, DW, AW = 4, 4, 8, 32


async def init_signals(dut):
    dut.en.value = 1
    dut.weight_start.value = 0
    dut.weight_matrix_flat.value = 0
    dut.act_in_flat.value = 0
    dut.act_valid_in.value = 0


async def load_weights(dut, B):
    """1 cycle start 펄스 → loader 가 다음 cycle 에 PE 에 broadcast"""
    flat = pack_flat([B[i][j] for i in range(R) for j in range(C)], DW)
    dut.weight_start.value = 1
    dut.weight_matrix_flat.value = flat
    await tick(dut)
    dut.weight_start.value = 0
    # loader 가 PE 에 load_weight 펄스 보내는 cycle (실제 PE 로딩)
    await tick(dut)
    # 이제 PE 들 weight_reg 에 값 적재 완료


async def stream_and_collect(dut, A):
    """A 를 parallel 입력 — input_skew 가 내부에서 staircase 적용.
    Output 은 valid_out=1 인 사이클의 result_flat 을 수집."""
    M = len(A)
    # row k 입력은 parallel — input_skew 가 row i 를 i cycle 지연
    # 외부에서는 매 cycle "한 row 의 모든 K 성분" 을 동시 입력하면 됨
    # 즉 cycle m 에 act_in_flat = [A[m][0], A[m][1], ..., A[m][R-1]]

    # systolic_top 의 총 latency:
    #   skew     : 0~R-1 cycle (row 별)
    #   pe_array : R + C - 1 cycle (wave 통과)
    #   collect  : +1 cycle (register)
    # 충분히 drain
    total = M + R + C + 4

    history_result = []
    history_valid = []
    for cyc in range(total):
        if cyc < M:
            act_vec = A[cyc]
            dut.act_in_flat.value = pack_flat(act_vec, DW)
            dut.act_valid_in.value = 1
        else:
            dut.act_in_flat.value = 0
            dut.act_valid_in.value = 0
        await tick(dut)
        history_result.append(read_signed_vec(dut.result_flat, C, AW))
        history_valid.append(int(dut.valid_out.value))

    return history_result, history_valid


def extract_result(history, M, base_offset):
    """history[base + m + j][j] = C[m][j]. base_offset 은 첫 의미 있는 사이클."""
    return [[history[base_offset + m + j][j] for j in range(C)] for m in range(M)]


def find_result_in_history(history, expected, M):
    """C[m][j] = history[base+m+j][j] 패턴으로 base 를 탐색"""
    for base in range(len(history) - M - C):
        try:
            cand = [[history[base + m + j][j] for j in range(C)] for m in range(M)]
            if cand == expected:
                return base
        except IndexError:
            continue
    return None


@cocotb.test()
async def test_identity_passthrough(dut):
    """B = I → C = A. C[m][j] 는 history[base+m+j][j] 패턴으로 등장."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    B = [[1 if i == j else 0 for j in range(C)] for i in range(R)]
    A = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
    expected = (np.array(A) @ np.array(B)).tolist()

    await load_weights(dut, B)
    history, valids = await stream_and_collect(dut, A)

    for cyc, (r, v) in enumerate(zip(history, valids)):
        cocotb.log.info(f"cyc={cyc}: valid={v}, result={r}")

    base = find_result_in_history(history, expected, len(A))
    assert base is not None, f"expected {expected} not found"
    cocotb.log.info(f"identity matched at base={base}")


@cocotb.test()
async def test_random_4x4(dut):
    """랜덤 weight + activation → NumPy 결과가 history 의 staircase 패턴에 등장"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    rng = np.random.default_rng(1)
    B = rng.integers(-6, 6, (R, C)).tolist()
    A = rng.integers(-6, 6, (5, R)).tolist()
    expected = (np.array(A) @ np.array(B)).tolist()

    await load_weights(dut, B)
    history, _ = await stream_and_collect(dut, A)

    cocotb.log.info(f"expected={expected}")
    base = find_result_in_history(history, expected, len(A))
    if base is None:
        for cyc, r in enumerate(history):
            cocotb.log.info(f"cyc={cyc}: result={r}")
    assert base is not None, f"expected not found"
    cocotb.log.info(f"matched at base={base}")
