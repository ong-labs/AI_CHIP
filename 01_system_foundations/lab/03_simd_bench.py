"""Reference for Week 1-3: SIMD intro and 700x decomposition."""
import os
import platform
import time

import numpy as np

np.seterr(over="ignore", divide="ignore", invalid="ignore")  # macOS Accelerate spurious warnings


def get_cpu_info() -> dict:
    info = {
        "cpu_brand": platform.processor() or "unknown",
        "clock_ghz": 3.0,
        "n_cores": os.cpu_count() or 8,
        "simd_lane_fp32": 4,
        "has_fma": True,
        "isa": "unknown (defaulted to 4-lane SIMD + FMA)",
        "source": "fallback",
    }
    try:
        import cpuinfo  # py-cpuinfo

        ci = cpuinfo.get_cpu_info()
        info["cpu_brand"] = ci.get("brand_raw", info["cpu_brand"])
        flags = set(ci.get("flags", []))
        if "avx512f" in flags:
            info["simd_lane_fp32"], info["isa"] = 16, "AVX-512"
        elif "avx2" in flags:
            info["simd_lane_fp32"], info["isa"] = 8, "AVX2"
        elif "avx" in flags:
            info["simd_lane_fp32"], info["isa"] = 8, "AVX"
        elif {"asimd", "neon"} & flags:
            info["simd_lane_fp32"], info["isa"] = 4, "NEON / AdvSIMD"
        info["has_fma"] = bool({"fma", "fma3", "asimd"} & flags)
        hz = ci.get("hz_advertised")
        if isinstance(hz, (list, tuple)) and hz and hz[0]:
            info["clock_ghz"] = hz[0] / 1e9
        info["source"] = "py-cpuinfo"
    except ImportError:
        pass
    return info


def theoretical_peak_gflops(info: dict) -> tuple[float, float]:
    fma_factor = 2 if info["has_fma"] else 1
    per_core = info["clock_ghz"] * info["simd_lane_fp32"] * fma_factor
    total = per_core * info["n_cores"]
    return per_core, total


def measured_numpy_matmul_gflops(N: int = 4096, n_runs: int = 3) -> float:
    A = np.random.rand(N, N).astype(np.float32)
    B = np.random.rand(N, N).astype(np.float32)
    _ = A @ B
    t0 = time.perf_counter()
    for _ in range(n_runs):
        _ = A @ B
    elapsed = (time.perf_counter() - t0) / n_runs
    return (2 * N**3) / elapsed / 1e9


def experiment_decomposition(N: int = 1_000_000) -> tuple[float, float, float, bool]:
    list_a = [float(i) for i in range(N)]
    list_b = [float(i) * 2 for i in range(N)]
    np_a = np.arange(N, dtype=np.float32)
    np_b = (np.arange(N) * 2).astype(np.float32)

    t0 = time.perf_counter()
    list_c = [list_a[i] + list_b[i] for i in range(N)]
    t_a = time.perf_counter() - t0

    np_c = np.empty(N, dtype=np.float32)
    t0 = time.perf_counter()
    for i in range(N):
        np_c[i] = np_a[i] + np_b[i]
    t_b = time.perf_counter() - t0

    _ = np_a + np_b
    n_runs = 20
    t0 = time.perf_counter()
    for _ in range(n_runs):
        np_c2 = np_a + np_b
    t_c = (time.perf_counter() - t0) / n_runs

    valid = np.allclose(list_c, np_c2) and np.allclose(np_c, np_c2)
    return t_a, t_b, t_c, valid


def main() -> None:
    info = get_cpu_info()
    print("=== Experiment 1: Theoretical peak vs measured ===")
    print(f"  CPU:           {info['cpu_brand']}")
    print(f"  Source:        {info['source']}")
    print(f"  Clock (assumed): {info['clock_ghz']:.2f} GHz")
    print(f"  Cores:         {info['n_cores']}")
    print(f"  SIMD ISA:      {info['isa']}")
    print(f"  FP32 lanes:    {info['simd_lane_fp32']}")
    print(f"  FMA:           {info['has_fma']}")

    per_core, total_peak = theoretical_peak_gflops(info)
    print(f"\n  Theoretical peak (single core): {per_core:>8.1f} GFLOPS")
    print(f"  Theoretical peak (all cores):   {total_peak:>8.1f} GFLOPS")

    measured = measured_numpy_matmul_gflops(N=4096)
    util = measured / total_peak * 100 if total_peak > 0 else 0
    print(f"\n  Measured NumPy MatMul (4096^2): {measured:>8.1f} GFLOPS")
    print(f"  Utilization:                    {util:>8.1f}% of all-core peak")
    if util > 100:
        print("\n  ⚠ Utilization > 100% — the simple peak formula understates this CPU.")
        print("    Likely cause: a matrix coprocessor (Apple AMX, Intel AMX-TILE) used by BLAS.")
        print("    The vector-lane formula doesn't capture matrix-engine throughput.")
        print(f"    For Week 1-4 use measured peak ≈ {measured:.0f} GFLOPS instead.")

    print("\n=== Experiment 2: 700x decomposition ===")
    N = 1_000_000
    print(f"Vector add, length N={N:,}\n")
    t_a, t_b, t_c, valid = experiment_decomposition(N=N)
    print(f"  (a) Python list  + Python loop:  {t_a*1000:>10.1f} ms")
    print(f"  (b) NumPy array  + Python loop:  {t_b*1000:>10.1f} ms")
    print(f"  (c) NumPy array  + vectorized:   {t_c*1000:>10.3f} ms")
    print(f"\n  (a) / (b) ratio (NumPy element boxing overhead): {t_a/t_b:>7.2f}x")
    print(f"  (b) / (c) ratio (SIMD + vectorization removes interpreter): {t_b/t_c:>7.0f}x")
    print(f"  (a) / (c) ratio (everything):                    {t_a/t_c:>7.0f}x")
    print(f"  Results match: {valid}")


if __name__ == "__main__":
    main()
