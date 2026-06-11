"""Week 3-4: integrated NPU simulator (analytical, weight-stationary).

Models a PE_R × PE_C systolic array with WS dataflow. Counts:
  - cycles  (streaming + tile-loop + DRAM transfer overlap)
  - energy  (MAC energy + DRAM/SRAM byte energy)
  - DRAM read/write bytes (with weight reuse across M-tiles)
  - PE utilization (fraction of PE-cycles doing real work)

The numerical result is computed via NumPy (functional simulator). Cycle counts
are analytical from the tile loop schedule, NOT cycle-accurate trace.
"""
import warnings
from dataclasses import dataclass

import numpy as np

from importlib.util import spec_from_file_location, module_from_spec
import os, sys

warnings.filterwarnings("ignore", category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _import_local(name: str, filename: str):
    spec = spec_from_file_location(name, os.path.join(_HERE, filename))
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cfg_mod = _import_local("npu_config_mod", "01_npu_architecture_bench.py")
_mm_mod = _import_local("npu_mac_mem_mod", "02_hardware_comp_bench.py")

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
Memory = _mm_mod.Memory
_MAC_ENERGY_PJ = _mm_mod._MAC_ENERGY_PJ


_DEFAULT_ACCUM = {"int8": "int32", "fp16": "fp32", "bf16": "fp32", "fp32": "fp32"}


@dataclass
class RunResult:
    C: np.ndarray
    cycles: int
    energy_pj: float
    dram_read_bytes: int
    dram_write_bytes: int
    pe_utilization: float

    @property
    def latency_ms(self) -> float:
        # caller multiplies by clock period; we'll attach this separately when printing
        return float("nan")


class NPU:
    def __init__(self, config: NPUConfig) -> None:
        self.config = config
        self.sram = Memory("SRAM", config.sram_bytes, 512, 2, 5.0)
        self.dram = Memory("DRAM", 32 * 1024**3, 200, 100, 100.0)
        accum = _DEFAULT_ACCUM[config.dtype]
        self._mac_energy_pj = _MAC_ENERGY_PJ.get((config.dtype, accum), 1.0)

    def _ceildiv(self, a: int, b: int) -> int:
        return (a + b - 1) // b

    def run(self, A: np.ndarray, B: np.ndarray) -> RunResult:
        M, K = A.shape
        K2, N = B.shape
        assert K == K2, f"K mismatch: {K} vs {K2}"

        pe_r = self.config.pe_array_rows
        pe_c = self.config.pe_array_cols
        bytes_e = self.config.dtype_bytes

        nt_m = self._ceildiv(M, pe_r)
        nt_n = self._ceildiv(N, pe_c)
        nt_k = self._ceildiv(K, pe_r)

        weight_tile_bytes = pe_r * pe_c * bytes_e
        input_tile_bytes = pe_r * pe_r * bytes_e
        output_tile_bytes = pe_r * pe_c * bytes_e

        # WS dataflow accounting:
        #  - Weight tile loaded once per (n_tile, k_tile); reused across M-tiles.
        #  - Input tile re-read per (m_tile, n_tile, k_tile) UNLESS full input fits in SRAM.
        #  - Output written once per (m_tile, n_tile).
        weight_full_bytes = nt_n * nt_k * weight_tile_bytes
        input_full_bytes = nt_m * nt_k * input_tile_bytes
        output_full_bytes = nt_m * nt_n * output_tile_bytes

        sram = self.config.sram_bytes
        if weight_full_bytes <= sram:
            weight_dram = weight_full_bytes
        else:
            # Weight too big for SRAM → re-read per m_tile (worst-case WS)
            weight_dram = nt_m * weight_full_bytes

        if input_full_bytes <= sram - min(weight_full_bytes, sram):
            input_dram = input_full_bytes
        else:
            input_dram = nt_n * input_full_bytes  # re-read per n_tile

        output_dram = output_full_bytes

        # Compute cycles: streaming through K-axis per tile + pipeline fill/drain
        cycles_per_tile = pe_r
        compute_cycles = nt_m * nt_n * nt_k * cycles_per_tile + (pe_r + pe_c - 1)

        # DRAM transfer cycles (clock-tied)
        dram_total_bytes = weight_dram + input_dram + output_dram
        bytes_per_cycle = self.config.dram_bw_gbps / self.config.clock_ghz
        dram_cycles = int(np.ceil(dram_total_bytes / bytes_per_cycle))
        # Compute and DRAM overlap: max of either, plus a fixed launch overhead
        total_cycles = max(compute_cycles, dram_cycles)
        # Per-call dispatch overhead (host → NPU command, ~1 μs at 1 GHz)
        OVERHEAD_CYCLES = int(self.config.clock_ghz * 1000)
        total_cycles += OVERHEAD_CYCLES

        # PE utilization
        full_pe_macs = nt_m * nt_n * nt_k * pe_r * pe_c * pe_r
        actual_macs = M * N * K
        pe_util = actual_macs / full_pe_macs if full_pe_macs > 0 else 0.0

        # Energy
        mac_energy = actual_macs * self._mac_energy_pj
        sram_accesses = dram_total_bytes  # each DRAM byte traverses SRAM at least once
        dram_energy = dram_total_bytes * self.dram.energy_pj_per_byte
        sram_energy = sram_accesses * self.sram.energy_pj_per_byte
        total_energy = mac_energy + dram_energy + sram_energy

        # Functional result at accumulator precision (mirrors real NPU behavior:
        # INT8 inputs → INT32 accumulator → INT32 result; user handles requant if needed).
        accum_np = {
            "int8": np.int32, "int16": np.int32, "int32": np.int32,
            "fp16": np.float32, "bf16": np.float32, "fp32": np.float32,
        }[self.config.dtype]
        C = (A.astype(accum_np) @ B.astype(accum_np))

        return RunResult(
            C=C,
            cycles=int(total_cycles),
            energy_pj=float(total_energy),
            dram_read_bytes=weight_dram + input_dram,
            dram_write_bytes=output_dram,
            pe_utilization=float(pe_util),
        )

    def latency_ms_from_cycles(self, cycles: int) -> float:
        return cycles / (self.config.clock_ghz * 1e9) * 1e3


def _print_test(label: str, cfg: NPUConfig, A: np.ndarray, B: np.ndarray, expected_util_range: tuple) -> bool:
    npu = NPU(cfg)
    r = npu.run(A, B)
    M, K = A.shape; _, N = B.shape
    accum_np = {
        "int8": np.int32, "int16": np.int32, "int32": np.int32,
        "fp16": np.float32, "bf16": np.float32, "fp32": np.float32,
    }[cfg.dtype]
    expected_C = (A.astype(accum_np) @ B.astype(accum_np))
    ok_C = np.allclose(r.C, expected_C, atol=1e-2)
    ok_util = expected_util_range[0] <= r.pe_utilization <= expected_util_range[1]
    print(f"\n[{label}]  M×K×N = {M}×{K}×{N}, PE = {cfg.pe_array_rows}×{cfg.pe_array_cols}")
    print(f"  cycles            = {r.cycles:,}")
    print(f"  latency           = {npu.latency_ms_from_cycles(r.cycles):.4f} ms @ {cfg.clock_ghz} GHz")
    print(f"  DRAM read bytes   = {r.dram_read_bytes:,} ({r.dram_read_bytes/1e6:.2f} MB)")
    print(f"  DRAM write bytes  = {r.dram_write_bytes:,}")
    print(f"  energy            = {r.energy_pj/1e9:.3f} mJ")
    print(f"  pe_utilization    = {r.pe_utilization:.3f}  (expected ∈ {expected_util_range})")
    print(f"  allclose          = {ok_C}")
    print(f"  PASS: {ok_C and ok_util}")
    return ok_C and ok_util


def main() -> None:
    cfg = make_reference_config()
    print("=== NPU Simulator Unit Tests ===")
    print(cfg.summary())

    rng = np.random.default_rng(0)
    int8 = lambda shape: rng.integers(-3, 4, size=shape, dtype=np.int8)

    pass_count = 0
    pass_count += _print_test(
        "Test 1: PE-array-exact",
        cfg,
        int8((16, 16)),
        int8((16, 16)),
        expected_util_range=(0.99, 1.0),
    )
    pass_count += _print_test(
        "Test 2: PE-array large multiple",
        cfg,
        int8((64, 64)),
        int8((64, 64)),
        expected_util_range=(0.99, 1.0),
    )
    pass_count += _print_test(
        "Test 3: smaller than PE array (underutilized)",
        cfg,
        int8((8, 8)),
        int8((8, 8)),
        expected_util_range=(0.10, 0.20),
    )
    pass_count += _print_test(
        "Test 4: non-square workload",
        cfg,
        int8((32, 128)),
        int8((128, 64)),
        expected_util_range=(0.99, 1.0),
    )

    print(f"\n=== {pass_count} / 4 tests passed ===")


if __name__ == "__main__":
    main()
