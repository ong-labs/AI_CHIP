"""Week 3-5: 5-workload measurement on student NPU + roofline + cross-comparison."""
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


def _import_local(name: str, filename: str):
    spec = spec_from_file_location(name, os.path.join(_HERE, filename))
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cfg_mod = _import_local("npu_config_mod", "01_npu_architecture_bench.py")
_sim_mod = _import_local("npu_sim_mod", "04_npu_simulator_bench.py")

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
NPU = _sim_mod.NPU


WORKLOADS = [
    ("W1 Tiny",            32,    32,   32),
    ("W2 LLM single",      1,   4096, 4096),
    ("W3 LLM batched",     256, 4096, 4096),
    ("W4 Large",           1024, 1024, 1024),  # smaller than full 4096^3 to keep run fast
    ("W5 Attn (K small)",  1024, 128, 1024),
]


def measure_npu(npu: NPU, m: int, k: int, n: int) -> dict:
    rng = np.random.default_rng(42)
    A = rng.integers(-3, 4, size=(m, k), dtype=np.int8)
    B = rng.integers(-3, 4, size=(k, n), dtype=np.int8)
    r = npu.run(A, B)
    flops = 2 * m * k * n
    latency_s = r.cycles / (npu.config.clock_ghz * 1e9)
    return {
        "cycles": r.cycles,
        "latency_ms": latency_s * 1e3,
        "tops_measured": flops / latency_s / 1e12,
        "dram_read_mb": r.dram_read_bytes / 1e6,
        "dram_write_mb": r.dram_write_bytes / 1e6,
        "energy_mj": r.energy_pj / 1e9,
        "pe_util": r.pe_utilization,
    }


def roofline_chart(npu: NPU, results: dict) -> None:
    cfg = npu.config
    peak_tops = cfg.peak_tops
    peak_bw = cfg.dram_bw_gbps  # GB/s

    fig, ax = plt.subplots(figsize=(9, 5))
    ai_range = np.logspace(-1, 4, 200)
    bw_roof = peak_bw * ai_range / 1e3  # GB/s × FLOPs/byte = GFLOPs → /1000 = TFLOPs
    compute_roof = np.full_like(ai_range, peak_tops)
    roof = np.minimum(bw_roof, compute_roof)
    ax.loglog(ai_range, roof, "k-", lw=2, label="Roofline")
    ax.axhline(peak_tops, color="gray", linestyle="--", alpha=0.5, label=f"peak {peak_tops:.2f} TOPS")

    for wname, (m, k, n) in zip([w[0] for w in WORKLOADS], [(w[1], w[2], w[3]) for w in WORKLOADS]):
        r = results[wname]
        flops = 2 * m * k * n
        bytes_total = (m * k + k * n + m * n) * cfg.dtype_bytes
        ai = flops / bytes_total
        ax.scatter([ai], [r["tops_measured"]], s=100, label=wname, zorder=5)

    ax.set_xlabel("Arithmetic Intensity (FLOPs/byte)")
    ax.set_ylabel("Throughput (TOPS)")
    ax.set_title(f"{cfg.name} — Roofline (peak {peak_tops:.2f} TOPS, BW {peak_bw} GB/s)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(output_dir / "04_npu_roofline.png", dpi=100)


def cross_compare_table(npu_results: dict) -> None:
    print("\n=== Cross-comparison with Week 2 chip catalog ===")
    print("(Approximate latency in ms, computed from peak roofline + 1 ms overhead floor)")
    OTHER_CHIPS = [
        ("CPU (M+AMX)",        3_000e9,  200e9,   16,   4, 0.5),
        ("RTX 4090",           82e12,    1008e9,  64,   4, 10.0),
        ("H100 (FP16)",        989e12,   3350e9,  128,  2, 8.0),
        ("TPU v4 (BF16)",      275e12,   1200e9,  128,  2, 20.0),
    ]

    print(f"{'Workload':<22}", end="")
    print(f"{'edu-NPU':>14}", end="")
    for name, *_ in OTHER_CHIPS:
        print(f"{name:>16}", end="")
    print()
    print("-" * (22 + 14 + 16 * len(OTHER_CHIPS)))

    for wname, m, k, n in WORKLOADS:
        print(f"{wname:<22}", end="")
        flops = 2 * m * k * n
        # Our NPU
        npu_t = npu_results[wname]["latency_ms"]
        print(f"{npu_t:>12.4f}ms", end="")
        for cname, peak, bw, reuse, dtype_b, ovh in OTHER_CHIPS:
            bytes_actual = (m * k + k * n + m * n) * dtype_b / max(reuse * min(min(m, k, n), 256) / 256, 1.0)
            t_c = flops / peak
            t_m = bytes_actual / bw
            t = max(t_c, t_m) * 1e3 + ovh / 1e3
            print(f"{t:>14.4f}ms", end="")
        print()


def main() -> None:
    cfg = make_reference_config()
    npu = NPU(cfg)

    print(f"=== Measuring {cfg.name} on 5 workloads ===\n")
    print(cfg.summary())
    print()
    print(
        f"{'Workload':<22} {'cycles':>10} {'lat (ms)':>10} "
        f"{'TOPS':>9} {'DRAM r MB':>10} {'energy mJ':>10} {'pe_util':>9}"
    )
    print("-" * 90)

    npu_results = {}
    for wname, m, k, n in WORKLOADS:
        r = measure_npu(npu, m, k, n)
        npu_results[wname] = r
        print(
            f"{wname:<22} {r['cycles']:>10,} {r['latency_ms']:>10.4f} "
            f"{r['tops_measured']:>9.4f} {r['dram_read_mb']:>10.2f} "
            f"{r['energy_mj']:>10.3f} {r['pe_util']:>9.3f}"
        )

    roofline_chart(npu, npu_results)
    print("\nSaved: 05_npu_roofline.png")

    cross_compare_table(npu_results)


if __name__ == "__main__":
    main()
