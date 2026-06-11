"""공통 cocotb 헬퍼 — 모든 testbench 에서 재사용.

cocotb 2.x 노트: RisingEdge 는 NBA 적용 *전* 리턴되므로,
post-edge 값 읽으려면 ReadOnly 까지 진행 필요.
`tick()` 가 그 boilerplate 를 캡슐화.
"""
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep


async def tick(dut):
    """1 cycle 진행 + NBA settle + write region 복귀"""
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()


async def reset_active_low(dut, hold_cycles: int = 2):
    """rst_n active-low 표준 reset. en, 기타 입력은 사전에 0으로 두고 호출."""
    dut.rst_n.value = 0
    for _ in range(hold_cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await tick(dut)


def pack_flat(values, width):
    """[v0, v1, v2, ...] → flat unsigned int (v_last 가 MSB)"""
    mask = (1 << width) - 1
    out = 0
    for i, v in enumerate(values):
        out |= (int(v) & mask) << (i * width)
    return out


def unpack_flat(flat, count, width, signed: bool = False):
    """flat → [v0, v1, ...]"""
    mask = (1 << width) - 1
    sign_bit = 1 << (width - 1)
    out = []
    for i in range(count):
        v = (int(flat) >> (i * width)) & mask
        if signed and (v & sign_bit):
            v -= (1 << width)
        out.append(v)
    return out


def read_signed_vec(signal, count, width):
    """flat reg/wire → list of signed ints"""
    raw = int(signal.value)
    return unpack_flat(raw, count, width, signed=True)
