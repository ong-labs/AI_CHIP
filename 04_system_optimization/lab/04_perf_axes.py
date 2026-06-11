"""Week 4-4: latency/throughput batching curve + cost model."""
import os
import sys
import warnings
from importlib.util import module_from_spec, spec_from_file_location

import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path

base_path = Path(__file__).resolve().parent
output_dir = base_path / "results"
output_dir.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings("ignore", category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
_W3 = os.path.join(_HERE, "..", "..", "03_npu_prototyping", "lab")


def _import_local(name: str, path: str):
    spec = spec_from_file_location(name, path)
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cfg_mod = _import_local("npu_config_mod", os.path.join(_W3, "01_npu_architecture_bench.py"))
_sim_mod = _import_local("npu_sim_mod", os.path.join(_W3, "04_npu_simulator_bench.py"))

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
NPU = _sim_mod.NPU


_AREA_PER_PE_MM2 = {"int8": 0.0005, "fp16": 0.002, "fp32": 0.008}
_AREA_PER_KB_MM2 = 0.0008
_FIXED_CTRL_AREA_MM2 = 5.0

_ENERGY_PJ_PER_MAC = {"int8": 0.20, "fp16": 1.10, "fp32": 3.70}


def estimate_die_area_mm2(cfg: NPUConfig) -> float:
    pe_area = cfg.n_pes * _AREA_PER_PE_MM2[cfg.dtype]
    sram_area = cfg.sram_kb * _AREA_PER_KB_MM2
    return pe_area + sram_area + _FIXED_CTRL_AREA_MM2


def estimate_power_w(cfg: NPUConfig, utilization: float) -> float:
    energy_per_op_pj = _ENERGY_PJ_PER_MAC[cfg.dtype]
    peak_power_w = cfg.peak_ops_per_sec * energy_per_op_pj * 1e-12
    return peak_power_w * utilization + 0.1 * peak_power_w  # +10% static


def batching_curve(cfg: NPUConfig, K: int, N: int, batches: list[int]) -> dict:
    npu = NPU(cfg)
    rng = np.random.default_rng(0)
    out = {"batch": [], "latency_ms": [], "throughput_qps": [], "pe_util": []}
    for B in batches:
        A = rng.integers(-3, 4, (B, K), dtype=np.int8)
        Bm = rng.integers(-3, 4, (K, N), dtype=np.int8)
        r = npu.run(A, Bm)
        latency_s = r.cycles / (cfg.clock_ghz * 1e9)
        out["batch"].append(B)
        out["latency_ms"].append(latency_s * 1e3)
        out["throughput_qps"].append(B / latency_s)
        out["pe_util"].append(r.pe_utilization)
    return out


def main() -> None:
    cfg = make_reference_config()
    print("=== Part A: Cost model on base config ===")
    print(cfg.summary())
    area = estimate_die_area_mm2(cfg)
    power_peak = estimate_power_w(cfg, 1.0)
    power_idle = estimate_power_w(cfg, 0.0)
    print(f"\n  Die area      : {area:.2f} mm²")
    print(f"  Peak power    : {power_peak:.3f} W (at full util)")
    print(f"  Idle power    : {power_idle:.3f} W")
    print(f"  Peak TOPS/W   : {cfg.peak_tops / power_peak:.3f}")

    print("\n=== Part B: Batching curve (K=4096, N=4096) ===")
    batches = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
    curve = batching_curve(cfg, K=4096, N=4096, batches=batches)
    print(f"\n{'batch':>6} {'lat (ms)':>10} {'QPS':>10} {'pe_util':>9}")
    print("-" * 40)
    for b, lat, qps, util in zip(curve["batch"], curve["latency_ms"], curve["throughput_qps"], curve["pe_util"]):
        print(f"{b:>6} {lat:>10.3f} {qps:>10.1f} {util:>9.3f}")

    max_qps = max(curve["throughput_qps"])
    knee_idx = next(
        (i for i, q in enumerate(curve["throughput_qps"]) if q >= max_qps * 0.95),
        len(batches) - 1,
    )
    print(f"\nKnee point (smallest batch reaching 95% of peak QPS):")
    print(f"  batch={curve['batch'][knee_idx]}, QPS={curve['throughput_qps'][knee_idx]:.1f}, "
          f"latency={curve['latency_ms'][knee_idx]:.3f} ms, pe_util={curve['pe_util'][knee_idx]:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.semilogx(batches, curve["latency_ms"], "o-")
    ax1.set_xlabel("Batch size (log)")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_title("Latency vs Batch")
    ax1.grid(True, which="both", alpha=0.3)
    ax2.loglog(batches, curve["throughput_qps"], "o-", color="tab:orange")
    ax2.set_xlabel("Batch size (log)")
    ax2.set_ylabel("Throughput (QPS, log)")
    ax2.set_title("Throughput vs Batch")
    ax2.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "03_batching_curve.png", dpi=100)
    print("\nSaved: 02_batching_curve.png")

    print("\n=== Part C: Cost-aware comparison (base vs alternatives) ===")
    alternatives = [
        ("base (16x16, 16MB, int8)", cfg),
    ]
    bigger_pe = type(cfg)(**{**cfg.__dict__, "name": "32×32 PE", "pe_array_rows": 32, "pe_array_cols": 32})
    bigger_sram = type(cfg)(**{**cfg.__dict__, "name": "64MB SRAM", "sram_kb": 65_536})
    fp16 = type(cfg)(**{**cfg.__dict__, "name": "FP16 dtype", "dtype": "fp16", "dtype_bytes": 2})
    alternatives += [(c.name, c) for c in (bigger_pe, bigger_sram, fp16)]

    print(f"\n{'config':<28} {'area mm²':>10} {'peak W':>10} {'peak TOPS':>11} {'TOPS/W':>9}")
    print("-" * 75)
    for label, c in alternatives:
        a = estimate_die_area_mm2(c)
        pw = estimate_power_w(c, 1.0)
        print(f"{label:<28} {a:>10.2f} {pw:>10.3f} {c.peak_tops:>11.3f} {c.peak_tops/pw:>9.3f}")


if __name__ == "__main__":
    main()
