"""Week 1-5: extended roofline with NPU + comparison chart."""
from dataclasses import dataclass

import matplotlib.pyplot as plt

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
    reuse: float
    dtype_bytes: int


HARDWARE = [
    HW("CPU (Apple M + AMX)", "fp32", 3_000e9, 200e9, 16, 4),
    HW("RTX 4090", "fp32", 82e12, 1008e9, 64, 4),
    HW("H100 (Tensor, FP16)", "fp16", 989e12, 3350e9, 128, 2),
    HW("TPU v4 (BF16)", "bf16", 275e12, 1200e9, 128, 2),
    HW("Apple Neural Engine", "int8", 15.8e12, 100e9, 32, 1),
]


def roofline(n: int, m: int, k: int, hw: HW) -> tuple[float, str]:
    flops = 2 * n * m * k
    bytes_actual = (n * k + k * m + n * m) * hw.dtype_bytes / hw.reuse
    t_c = flops / hw.peak_ops_per_sec
    t_m = bytes_actual / hw.peak_bw_bps
    return (t_c, "compute") if t_c >= t_m else (t_m, "memory")


def main() -> None:
    N = 4096
    print("=" * 92)
    print(f"MatMul {N}x{N}x{N} predictions across hardware")
    print("=" * 92)
    header = (
        f"{'Hardware':<23}{'dtype':<7}{'peak T':>9}{'BW GB/s':>10}"
        f"{'time ms':>11}{'TOPS meas':>12}  {'bound':<10}{'speedup':>9}"
    )
    print(header)
    print("-" * 92)

    rows = []
    for hw in HARDWARE:
        t, bound = roofline(N, N, N, hw)
        tops = (2 * N**3) / t / 1e12
        rows.append((hw, t, bound, tops))

    cpu_t = rows[0][1]
    for hw, t, bound, tops in rows:
        peak_t = hw.peak_ops_per_sec / 1e12
        bw_g = hw.peak_bw_bps / 1e9
        sp = cpu_t / t
        print(
            f"{hw.name:<23}{hw.dtype:<7}{peak_t:>9.1f}{bw_g:>9.0f} "
            f"{t*1000:>10.4f}   {tops:>10.1f}  {bound:<10}{sp:>8.1f}x"
        )

    names = [hw.name for hw, *_ in rows]
    speedups = [cpu_t / t for _, t, *_ in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#888888", "#76b900", "#76b900", "#4a90d9", "#a259d9"]
    bars = ax.bar(range(len(names)), speedups, color=colors)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Speedup vs CPU (log scale)")
    ax.set_yscale("log")
    ax.set_title(f"Predicted MatMul {N}^3 speedup")
    ax.grid(True, which="both", alpha=0.3, axis="y")
    for bar, sp in zip(bars, speedups):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{sp:.1f}x",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(output_dir / "05_cpu_gpu_npu_compare.png", dpi=100)
    print("\nSaved: 05_cpu_gpu_npu_compare.png")


if __name__ == "__main__":
    main()