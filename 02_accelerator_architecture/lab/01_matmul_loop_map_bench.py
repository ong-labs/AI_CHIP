"""Week 2-1: 6 loop orderings of MatMul + stationary classification."""
import time

import numpy as np

np.seterr(over="ignore", divide="ignore", invalid="ignore")


def matmul_ijk(A, B, C):
    M, K = A.shape; _, N = B.shape
    for i in range(M):
        for j in range(N):
            for k in range(K):
                C[i, j] += A[i, k] * B[k, j]


def matmul_ikj(A, B, C):
    M, K = A.shape; _, N = B.shape
    for i in range(M):
        for k in range(K):
            for j in range(N):
                C[i, j] += A[i, k] * B[k, j]


def matmul_jik(A, B, C):
    M, K = A.shape; _, N = B.shape
    for j in range(N):
        for i in range(M):
            for k in range(K):
                C[i, j] += A[i, k] * B[k, j]


def matmul_jki(A, B, C):
    M, K = A.shape; _, N = B.shape
    for j in range(N):
        for k in range(K):
            for i in range(M):
                C[i, j] += A[i, k] * B[k, j]


def matmul_kij(A, B, C):
    M, K = A.shape; _, N = B.shape
    for k in range(K):
        for i in range(M):
            for j in range(N):
                C[i, j] += A[i, k] * B[k, j]


def matmul_kji(A, B, C):
    M, K = A.shape; _, N = B.shape
    for k in range(K):
        for j in range(N):
            for i in range(M):
                C[i, j] += A[i, k] * B[k, j]


ORDERINGS = [
    ("ijk", matmul_ijk, "k", "C", "Output Stationary"),
    ("ikj", matmul_ikj, "j", "A", "Input Stationary"),
    ("jik", matmul_jik, "k", "C", "Output Stationary"),
    ("jki", matmul_jki, "i", "B", "Weight Stationary"),
    ("kij", matmul_kij, "j", "A", "Input Stationary"),
    ("kji", matmul_kji, "i", "B", "Weight Stationary"),
]


def main(N: int = 120) -> None:
    np.random.seed(0)
    A = np.random.rand(N, N).astype(np.float32)
    B = np.random.rand(N, N).astype(np.float32)
    C_ref = A @ B

    print(f"MatMul {N}x{N} float32, 6 loop orderings\n")
    print(f"{'Order':<6} {'inner':<6} {'stat var':<9} {'classification':<20} {'time (s)':>10} {'allclose':>10}")
    print("-" * 70)

    results = []
    for name, fn, inner, stat_var, stat_class in ORDERINGS:
        C = np.zeros((N, N), dtype=np.float32)
        t0 = time.perf_counter()
        fn(A, B, C)
        elapsed = time.perf_counter() - t0
        ok = np.allclose(C, C_ref, atol=1e-3)
        print(f"{name:<6} {inner:<6} {stat_var:<9} {stat_class:<20} {elapsed:>10.3f} {str(ok):>10}")
        results.append((name, elapsed))

    fastest = min(results, key=lambda x: x[1])
    slowest = max(results, key=lambda x: x[1])
    print(f"\nFastest: {fastest[0]} ({fastest[1]:.3f}s)")
    print(f"Slowest: {slowest[0]} ({slowest[1]:.3f}s)")
    print(f"Ratio:   {slowest[1]/fastest[1]:.2f}x")
    print(f"\nNumPy A @ B for comparison:")
    _ = A @ B
    t0 = time.perf_counter()
    for _ in range(100):
        _ = A @ B
    np_time = (time.perf_counter() - t0) / 100
    print(f"  NumPy:  {np_time:.6f}s ({fastest[1]/np_time:.0f}x faster than fastest Python ordering)")


if __name__ == "__main__":
    main()
