"""Week 1-1: for-loop vs NumPy MatMul."""

import time

import numpy as np

np.seterr(over="ignore", divide="ignore", invalid="ignore")  # macOS Accelerate spurious warnings


def matmul_loop(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    M, K = A.shape
    K2, N = B.shape
    assert K == K2
    C = np.zeros((M, N), dtype=A.dtype)
    for i in range(M):
        for j in range(N):
            for k in range(K):
                C[i, j] += A[i, k] * B[k, j]
    return C


def main(N: int = 200) -> None:
    np.random.seed(0)
    A = np.random.rand(N, N).astype(np.float32)
    B = np.random.rand(N, N).astype(np.float32)
    flops = 2 * N**3

    print(f"MatMul {N}x{N} float32 — {flops:,} FLOPs\n")

    print("Running pure Python loop (this takes a moment)...")
    t0 = time.perf_counter()
    C_loop = matmul_loop(A, B)
    t_loop = time.perf_counter() - t0
    print(f"  Loop:  {t_loop:>8.3f} s    ({flops/t_loop/1e9:>7.4f} GFLOPs)")

    _ = A @ B
    n_runs = 10
    t0 = time.perf_counter()
    for _ in range(n_runs):
        C_np = A @ B
    t_np = (time.perf_counter() - t0) / n_runs
    print(f"  NumPy: {t_np*1000:>8.3f} ms   ({flops/t_np/1e9:>7.1f} GFLOPs)")

    print(f"\n  Speedup: {t_loop/t_np:.0f}x")
    print(f"  allclose (atol=1e-3): {np.allclose(C_loop, C_np, atol=1e-3)}")


if __name__ == "__main__":
    main()
