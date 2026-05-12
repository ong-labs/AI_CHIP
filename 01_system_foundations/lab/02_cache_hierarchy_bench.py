"""Week 1-2: cache hierarchy effects via pointer chasing + access pattern."""

import time

import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path

base_path = Path(__file__).resolve().parent
output_dir = base_path / "results"
output_dir.mkdir(parents=True, exist_ok=True)

np.seterr(over="ignore", divide="ignore", invalid="ignore")


def pointer_chase(sizes_kb: list[int], steps_per_size: int = 200_000) -> tuple[list[int], list[float]]:
    """Each step depends on the previous → defeats prefetcher → reveals cache hierarchy."""
    times_ns = []
    for size_kb in sizes_kb:
        n = max(2, size_kb * 1024 // 8)
        perm = np.random.permutation(n).astype(np.int64)

        i = 0
        for _ in range(min(1000, n)):
            i = int(perm[i])

        t0 = time.perf_counter()
        i = 0
        for _ in range(steps_per_size):
            i = int(perm[i])
        elapsed = time.perf_counter() - t0
        times_ns.append(elapsed / steps_per_size * 1e9)
        _ = i
    return sizes_kb, times_ns


def row_vs_col_numpy(N: int = 4096, n_runs: int = 10) -> tuple[float, float, bool]:
    A = np.random.rand(N, N).astype(np.float32)
    A.sum(axis=1); A.sum(axis=0)

    t0 = time.perf_counter()
    for _ in range(n_runs):
        s_row = A.sum(axis=1)
    row_t = (time.perf_counter() - t0) / n_runs

    t0 = time.perf_counter()
    for _ in range(n_runs):
        s_col = A.sum(axis=0)
    col_t = (time.perf_counter() - t0) / n_runs

    return row_t, col_t, np.allclose(s_row.sum(), s_col.sum(), rtol=1e-3)


def fmt_size(kb: int) -> str:
    return f"{kb} KB" if kb < 1024 else f"{kb // 1024} MB"


def main() -> None:
    print("=== Experiment 1: Pointer chasing (cache hierarchy via latency) ===")
    sizes = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144]
    sizes_kb, times_ns = pointer_chase(sizes)
    print(f"\n{'Size':>10}  {'ns/access':>11}")
    for sz, t in zip(sizes_kb, times_ns):
        print(f"{fmt_size(sz):>10}  {t:>10.1f}")

    plt.figure(figsize=(8, 5))
    plt.semilogx(sizes_kb, times_ns, "o-")
    plt.xlabel("Working set (KB, log)")
    plt.ylabel("Pointer chase latency (ns/step)")
    plt.title("Cache hierarchy via pointer chasing")
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "02_working_set_result.png", dpi=100)
    print("\nSaved: 02_working_set_result.png")

    print("\n=== Experiment 2: NumPy row vs column sum (axis=1 vs axis=0) ===")
    N = 4096
    print(f"Matrix: {N}x{N} float32 ({N*N*4/1e6:.0f} MB)")
    row_t, col_t, valid = row_vs_col_numpy(N=N)
    print(f"  axis=1 (row-wise, contiguous): {row_t*1000:.2f} ms")
    print(f"  axis=0 (col-wise, strided):    {col_t*1000:.2f} ms")
    print(f"  Ratio col/row: {col_t/row_t:.2f}x")
    print(f"  Sum totals match: {valid}")
    if col_t < row_t * 1.2:
        print()
        print("  ℹ NOTE — col_t ≤ row_t on this platform.")
        print("    Some BLAS (Apple Accelerate, recent OpenBLAS) implement axis=0 as a")
        print("    *streaming* reduction: walk the contiguous storage once, accumulate")
        print("    into a small column-output buffer that fits in L1. The 'strided' assumption")
        print("    breaks. Cache effect is best seen via Experiment 1 (pointer chasing).")


if __name__ == "__main__":
    main()
