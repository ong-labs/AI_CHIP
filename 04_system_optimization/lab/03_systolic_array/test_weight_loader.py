"""test_weight_loader.py — 1-cycle broadcast 로더 검증."""
import cocotb
from cocotb.clock import Clock

from cocotb_helpers import tick, reset_active_low, pack_flat, read_signed_vec


ROWS, COLS, DW = 4, 4, 8


async def init_signals(dut):
    dut.start.value = 0
    dut.weight_matrix_flat.value = 0


@cocotb.test()
async def test_load_pulse(dut):
    """start=1 펄스 → 다음 cycle load_weight_flat=all 1, weight_out=입력 그대로"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    W = [[1, 2, 3, 4],
         [5, 6, 7, 8],
         [9, 10, 11, 12],
         [13, 14, 15, 16]]
    w_flat_val = pack_flat([W[i][j] for i in range(ROWS) for j in range(COLS)], DW)

    # 초기 상태: load=0, done=0
    assert int(dut.load_weight_flat.value) == 0
    assert int(dut.done.value) == 0

    # start 펄스
    dut.start.value = 1
    dut.weight_matrix_flat.value = w_flat_val
    await tick(dut)

    # 이 cycle 직후: load_weight_flat = all-1, weight_out = w_flat_val
    load_val = int(dut.load_weight_flat.value)
    weight_out = read_signed_vec(dut.weight_out_flat, ROWS * COLS, DW)
    cocotb.log.info(f"after start: load_flat=0x{load_val:x}, weight_out={weight_out}")
    assert load_val == (1 << (ROWS * COLS)) - 1, f"all PE load 가 아닌데? 0x{load_val:x}"
    expected_w = [W[i][j] for i in range(ROWS) for j in range(COLS)]
    assert weight_out == expected_w

    # start=0 으로 떨어뜨림
    dut.start.value = 0
    await tick(dut)

    # 이 cycle 직후: load_weight_flat=0, done=1
    assert int(dut.load_weight_flat.value) == 0
    assert int(dut.done.value) == 1
    cocotb.log.info("done asserted in next cycle ✓")

    # 한 cycle 더: done=0 (sticky 아님)
    await tick(dut)
    assert int(dut.done.value) == 0


@cocotb.test()
async def test_no_start(dut):
    """start=0 유지 시 load_weight 발생 안 함"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    for _ in range(10):
        await tick(dut)
        assert int(dut.load_weight_flat.value) == 0
        assert int(dut.done.value) == 0
