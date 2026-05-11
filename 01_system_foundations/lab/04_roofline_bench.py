"""Week 1-4: roofline model + CPU validation + GPU prediction."""
import time
from dataclasses import dataclass

import numpy as np

np.seterr(over="ignore", divide="ignore", invalid="ignore")  # macOS Accelerate spurious warnings


@dataclass
class RooflineResult:
    time_s: float
    gflops: float
    ai: float
    bound: str


def roofline_estimate(
    n: int,
    m: int,
    k: int,
    peak_gflops: float,
    peak_bw_gbps: float,
    reuse_factor: float = 1.0,
    dtype_bytes: int = 4,
) -> RooflineResult:
    flops = 2 * n * m * k
    bytes_naive = (n * k + k * m + n * m) * dtype_bytes
    bytes_actual = bytes_naive / reuse_factor
    t_compute = flops / (peak_gflops * 1e9)
    t_memory = bytes_actual / (peak_bw_gbps * 1e9)
    if t_compute >= t_memory:
        return RooflineResult(t_compute, peak_gflops, flops / bytes_actual, "compute")
    return RooflineResult(t_memory, flops / t_memory / 1e9, flops / bytes_actual, "memory")


SPECS_FP32 = {
    "CPU (Apple M-class + AMX)": {"peak_gflops": 3_000, "peak_bw": 200, "reuse": 16},
    "RTX 4090": {"peak_gflops": 82_000, "peak_bw": 1008, "reuse": 64},
    "H100 SXM (FP32)": {"peak_gflops": 67_000, "peak_bw": 3350, "reuse": 128},
    "Apple M2 GPU": {"peak_gflops": 3_600, "peak_bw": 100, "reuse": 32},
}


def measured_cpu_matmul(N: int, n_runs: int = 3) -> tuple[float, float]:
    A = np.random.rand(N, N).astype(np.float32)
    B = np.random.rand(N, N).astype(np.float32)
    _ = A @ B
    t0 = time.perf_counter()
    for _ in range(n_runs):
        _ = A @ B
    elapsed = (time.perf_counter() - t0) / n_runs
    gflops = (2 * N**3) / elapsed / 1e9
    return gflops, elapsed


def main() -> None:
    print("=== Part 1: Validate roofline model on CPU ===")
    cpu = SPECS_FP32["CPU (Apple M-class + AMX)"]
    for N in (2048, 4096):
        pred = roofline_estimate(N, N, N, cpu["peak_gflops"], cpu["peak_bw"], cpu["reuse"])
        meas_gflops, meas_t = measured_cpu_matmul(N)
        print(f"\n  N={N}")
        print(f"    Predicted: {pred.time_s*1000:>10.2f} ms ({pred.gflops:>7.0f} GFLOPS, {pred.bound})")
        print(f"    Measured:  {meas_t*1000:>10.2f} ms ({meas_gflops:>7.0f} GFLOPS)")
        print(f"    Ratio (predicted / measured time): {pred.time_s/meas_t:.2f}x")

    print("\n=== Part 2: GPU predictions (model unchanged, parameters changed) ===")
    cpu_4k = roofline_estimate(4096, 4096, 4096, cpu["peak_gflops"], cpu["peak_bw"], cpu["reuse"]).time_s

    print(f"\n{'Hardware':<28} {'N=2048 ms':>12} {'N=4096 ms':>12}  {'bound (4k)':>12}  {'speedup vs CPU':>16}")
    print("-" * 86)
    for name, spec in SPECS_FP32.items():
        r2k = roofline_estimate(2048, 2048, 2048, spec["peak_gflops"], spec["peak_bw"], spec["reuse"])
        r4k = roofline_estimate(4096, 4096, 4096, spec["peak_gflops"], spec["peak_bw"], spec["reuse"])
        speedup = cpu_4k / r4k.time_s
        print(f"{name:<28} {r2k.time_s*1000:>10.4f}   {r4k.time_s*1000:>10.4f}   {r4k.bound:>10}    {speedup:>14.1f}x")


if __name__ == "__main__":
    main()
