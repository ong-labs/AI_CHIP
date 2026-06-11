"""test_input_skew.py — input_skew (계단형 지연) 검증."""
import cocotb
from cocotb.clock import Clock

from cocotb_helpers import tick, reset_active_low, pack_flat, read_signed_vec


ROWS, DW = 4, 8


async def init_signals(dut):
    dut.en.value = 1
    dut.act_in_flat.value = 0


@cocotb.test()
async def test_staircase_pattern(dut):
    """row i 의 입력이 (i-1) test-cycle 후 출력으로 나오는지.

    Note: 본 모듈은 *systolic 용* 이라 pe_array 가 edge-BEFORE-NBA 로 읽음 → i cycle 지연.
    cocotb 가 AFTER-NBA 로 읽으면 1 cycle 일찍 보이므로 test-delay = i-1 (row 0 은 0).
    """
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    history_out = []
    for cyc in range(ROWS + 4):
        vec_in = [cyc + 1] * ROWS   # 0 과 구분 위해 +1
        dut.act_in_flat.value = pack_flat(vec_in, DW)
        await tick(dut)
        vec_out = read_signed_vec(dut.act_out_flat, ROWS, DW)
        history_out.append(vec_out)
        cocotb.log.info(f"cyc={cyc}: in={vec_in}, out={vec_out}")

    # out[cyc][0] = cyc+1 (pass-through, no delay)
    # out[cyc][i] = (cyc-i+1)+1 = cyc-i+2  if cyc >= i-1 else 0   (k registers → k-1 test-delay)
    for cyc in range(ROWS + 4):
        for i in range(ROWS):
            if i == 0:
                expected = cyc + 1
            elif cyc >= i - 1:
                expected = cyc - i + 2
            else:
                expected = 0
            assert history_out[cyc][i] == expected, \
                f"cyc={cyc} row={i}: got {history_out[cyc][i]}, expect {expected}"


@cocotb.test()
async def test_pulse_propagation(dut):
    """1 cycle 펄스만 입력, 각 row 에서 (i-1) test-cycle 후 한 번만 나오는지 (row 0 은 즉시)"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    pulse_seen = [None] * ROWS
    for cyc in range(ROWS + 2):
        vec_in = [99] * ROWS if cyc == 0 else [0] * ROWS
        dut.act_in_flat.value = pack_flat(vec_in, DW)
        await tick(dut)
        vec_out = read_signed_vec(dut.act_out_flat, ROWS, DW)
        for i in range(ROWS):
            if vec_out[i] == 99 and pulse_seen[i] is None:
                pulse_seen[i] = cyc

    cocotb.log.info(f"pulse_seen={pulse_seen}")
    # row 0: cyc 0 (즉시), row i>=1: cyc (i-1)
    for i in range(ROWS):
        expected = 0 if i == 0 else i - 1
        assert pulse_seen[i] == expected, \
            f"row {i}: pulse seen at cyc {pulse_seen[i]}, expect {expected}"


@cocotb.test()
async def test_enable_holds(dut):
    """en=0 동안 모든 stage 정지"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    # 먼저 모든 stage 에 데이터 채우기
    for cyc in range(ROWS):
        dut.act_in_flat.value = pack_flat([cyc + 1] * ROWS, DW)
        await tick(dut)

    snapshot = read_signed_vec(dut.act_out_flat, ROWS, DW)
    cocotb.log.info(f"before en=0: out={snapshot}")

    # en=0, 가짜 입력 5 cycle
    dut.en.value = 0
    dut.act_in_flat.value = pack_flat([99] * ROWS, DW)
    for _ in range(5):
        await tick(dut)

    after = read_signed_vec(dut.act_out_flat, ROWS, DW)
    cocotb.log.info(f"after en=0: out={after}")
    # row 0 은 pass-through 이므로 입력 그대로 보임 (99). row 1+ 는 reg held.
    assert after[0] == 99, "row 0 (pass-through) should reflect current input"
    for i in range(1, ROWS):
        assert after[i] == snapshot[i], f"row {i} changed under en=0"
