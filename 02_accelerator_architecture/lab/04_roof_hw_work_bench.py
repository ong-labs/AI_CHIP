"""Week 2-4: roofline + TPU added, workload × hardware comparison."""
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path

base_path = Path(__file__).resolve().parent
output_dir = base_path / "results"
output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class HW:
    name: str
    dtype: str
    peak_ops_per_sec: float
    peak_bw_bps: float
    base_reuse: float
    dtype_bytes: int
    overhead_us: float  # kernel-launch / dispatch overhead, models real-world tiny-workload penalty


HARDWARE = [
    HW("CPU (M+AMX)",        "fp32", 3_000e9,    200e9,   16,  4,   0.5),
    HW("RTX 4090",           "fp32", 82e12,      1008e9,  64,  4,  10.0),
    HW("H100 (Tensor FP16)", "fp16", 989e12,     3350e9,  128, 2,   8.0),
    HW("TPU v4 (BF16)",      "bf16", 275e12,     1200e9,  128, 2,  20.0),
    HW("Apple NE",           "int8", 15.8e12,    100e9,   32,  1, 100.0),
]


WORKLOADS = [
    ("W1 Tiny",             32, 32, 32),
    ("W2 LLM single",       1, 4096, 4096),
    ("W3 LLM batched",      256, 4096, 4096),
    ("W4 Large",            4096, 4096, 4096),
    ("W5 Attn (K small)",   1024, 128, 1024),
]


def effective_reuse(hw: HW, m: int, k: int, n: int) -> float:
    """Penalize reuse for tiny workloads (PE underutilization).

    For systolic-style hardware, reuse ≈ min(workload_dim, array_dim).
    We approximate with: base_reuse × min(min(m,n,k), 256) / 256.
    """
    smallest = min(m, n, k)
    eff = hw.base_reuse * min(smallest, 256) / 256
    return max(eff, 1.0)


def roofline(m: int, k: int, n: int, hw: HW) -> tuple[float, str]:
    flops = 2 * m * k * n
    reuse = effective_reuse(hw, m, k, n)
    bytes_actual = (m * k + k * n + m * n) * hw.dtype_bytes / reuse
    t_c = flops / hw.peak_ops_per_sec
    t_m = bytes_actual / hw.peak_bw_bps
    t_kernel = max(t_c, t_m)
    bound = "compute" if t_c >= t_m else "memory"
    t_total = t_kernel + hw.overhead_us * 1e-6
    if hw.overhead_us * 1e-6 > t_kernel * 2:
        bound = "overhead"
    return t_total, bound


def main() -> None:
    col_w = 22
    total_w = 22 + col_w * len(HARDWARE) + 18
    print("=" * total_w)
    print(f"{'Workload':<22}", end="")
    for hw in HARDWARE:
        print(f"{hw.name:>{col_w}}", end="")
    print(f"  {'winner':>16}")
    print("-" * total_w)

    cell_times = {}
    for wname, m, k, n in WORKLOADS:
        print(f"{wname:<22}", end="")
        row_times = {}
        for hw in HARDWARE:
            t, bound = roofline(m, k, n, hw)
            row_times[hw.name] = (t, bound)
            cell_times[(wname, hw.name)] = t
            t_us = t * 1e6
            if t_us < 1000:
                cell = f"{t_us:>9.1f}us {bound[0]}"
            else:
                cell = f"{t*1000:>9.3f}ms {bound[0]}"
            print(f"{cell:>{col_w}}", end="")
        winner = min(row_times.items(), key=lambda kv: kv[1][0])
        winner_short = winner[0].split()[0]
        print(f"  {winner_short:>16}")

    print("\nLegend: 'c'=compute, 'm'=memory, 'o'=overhead-bound")

    print("\n--- Per-hardware speedup vs CPU on each workload ---")
    print(f"{'Workload':<22}", end="")
    for hw in HARDWARE[1:]:
        print(f"{hw.name:>22}", end="")
    print()
    cpu_name = HARDWARE[0].name
    for wname, *_ in WORKLOADS:
        print(f"{wname:<22}", end="")
        cpu_t = cell_times[(wname, cpu_name)]
        for hw in HARDWARE[1:]:
            sp = cpu_t / cell_times[(wname, hw.name)]
            print(f"{sp:>20.1f}x", end="")
        print()

    workload_names = [w[0] for w in WORKLOADS]
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.16
    x = np.arange(len(workload_names))
    cpu_t_list = np.array([cell_times[(w, cpu_name)] for w in workload_names])
    for i, hw in enumerate(HARDWARE):
        speedups = np.array([cell_times[(w, cpu_name)] / cell_times[(w, hw.name)] for w in workload_names])
        ax.bar(x + (i - 2) * width, speedups, width, label=hw.name)
    ax.set_xticks(x)
    ax.set_xticklabels(workload_names, rotation=15, ha="right")
    ax.set_ylabel("Speedup vs CPU (log)")
    ax.set_yscale("log")
    ax.set_title("Hardware speedup per workload (roofline prediction)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, axis="y", which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "04_workload_compare.png", dpi=100)
    print("\nSaved: 04_workload_compare.png")


if __name__ == "__main__":
    main()
