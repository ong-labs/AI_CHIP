"""test_output_collect.py — psum capture + valid pipeline 검증."""
import cocotb
from cocotb.clock import Clock

from cocotb_helpers import tick, reset_active_low, pack_flat, read_signed_vec


COLS, AW = 4, 32


async def init_signals(dut):
    dut.en.value = 1
    dut.psum_in_flat.value = 0
    dut.valid_in.value = 0


@cocotb.test()
async def test_capture_and_valid(dut):
    """psum_in 이 1 cycle 후 result 로, valid_in 이 1 cycle 후 valid_out 으로"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    # cycle 0: psum_in = [10, 20, 30, 40], valid_in = 1
    vec = [10, 20, 30, 40]
    dut.psum_in_flat.value = pack_flat(vec, AW)
    dut.valid_in.value = 1
    await tick(dut)

    # 이 cycle 직후: result = vec, valid_out = 1
    result = read_signed_vec(dut.result_flat, COLS, AW)
    cocotb.log.info(f"result={result}, valid_out={int(dut.valid_out.value)}")
    assert result == vec
    assert int(dut.valid_out.value) == 1

    # valid_in 떨어뜨리면 valid_out 도 1 cycle 후 떨어짐
    dut.valid_in.value = 0
    dut.psum_in_flat.value = 0
    await tick(dut)
    assert int(dut.valid_out.value) == 0
    assert read_signed_vec(dut.result_flat, COLS, AW) == [0, 0, 0, 0]


@cocotb.test()
async def test_enable_holds(dut):
    """en=0 동안 result/valid 동결"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await init_signals(dut)
    await reset_active_low(dut)

    vec = [100, 200, 300, 400]
    dut.psum_in_flat.value = pack_flat(vec, AW)
    dut.valid_in.value = 1
    await tick(dut)
    held_result = read_signed_vec(dut.result_flat, COLS, AW)
    assert held_result == vec

    dut.en.value = 0
    dut.psum_in_flat.value = pack_flat([9, 9, 9, 9], AW)
    dut.valid_in.value = 0
    for _ in range(3):
        await tick(dut)

    after = read_signed_vec(dut.result_flat, COLS, AW)
    assert after == held_result, "result changed under en=0"
    assert int(dut.valid_out.value) == 1, "valid_out changed under en=0"
