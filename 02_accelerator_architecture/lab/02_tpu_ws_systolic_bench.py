"""Week 2-2: cycle-by-cycle weight-stationary systolic array simulator."""
import numpy as np

np.seterr(over="ignore", divide="ignore", invalid="ignore")


class SystolicArray:
    """Weight-stationary K×N PE array.

    State per PE:
      - weight (loaded once, stationary)
      - pe_input  : input value currently held (will shift right next cycle)
      - pe_ps_in  : partial-sum coming in from above (becomes ps_out + input·weight after compute)

    Each step():
      1. ps_out[k,n] = pe_ps_in[k,n] + pe_input[k,n] * weight[k,n]
      2. Bottom row's ps_out is emitted as output.
      3. pe_input shifts right by one column; leftmost column gets new external feed.
      4. pe_ps_in shifts down by one row; top row remains 0.
    """

    def __init__(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        self.weights = np.zeros((rows, cols), dtype=np.float32)
        self.pe_input = np.zeros((rows, cols), dtype=np.float32)
        self.pe_ps_in = np.zeros((rows, cols), dtype=np.float32)
        self.cycle = 0

    def reset(self) -> None:
        self.weights[:] = 0
        self.pe_input[:] = 0
        self.pe_ps_in[:] = 0
        self.cycle = 0

    def load_weights(self, B: np.ndarray) -> None:
        assert B.shape == (self.rows, self.cols)
        self.weights[:] = B

    def step(self, left_inputs: np.ndarray) -> np.ndarray:
        ps_out = self.pe_ps_in + self.pe_input * self.weights
        bottom = ps_out[-1].copy()

        new_pe_input = np.zeros_like(self.pe_input)
        new_pe_input[:, 1:] = self.pe_input[:, :-1]
        new_pe_input[:, 0] = left_inputs

        new_pe_ps_in = np.zeros_like(self.pe_ps_in)
        new_pe_ps_in[1:] = ps_out[:-1]

        self.pe_input = new_pe_input
        self.pe_ps_in = new_pe_ps_in
        self.cycle += 1
        return bottom

    def run(self, A: np.ndarray, B: np.ndarray, trace: bool = False) -> tuple[np.ndarray, int]:
        M, K = A.shape
        K2, N = B.shape
        assert K == K2 == self.rows
        assert N == self.cols

        self.reset()
        self.load_weights(B)

        outputs_per_cycle = []
        max_cycle = M + K + N
        for t in range(max_cycle):
            left = np.zeros(K, dtype=np.float32)
            for k in range(K):
                m = t - k
                if 0 <= m < M:
                    left[k] = A[m, k]
            bottom = self.step(left)
            outputs_per_cycle.append(bottom.copy())
            if trace:
                print(f"  cycle {t}: left={left.tolist()}  bottom={bottom.tolist()}")
                with np.printoptions(precision=3, suppress=True):
                    print(f"    pe_ps_in:\n{self.pe_ps_in}")

        C = np.zeros((M, N), dtype=np.float32)
        for m in range(M):
            for n in range(N):
                t_out = m + K + n
                if t_out < len(outputs_per_cycle):
                    C[m, n] = outputs_per_cycle[t_out][n]
        return C, self.cycle


def main() -> None:
    np.random.seed(0)
    M, K, N = 4, 4, 4
    A = np.random.rand(M, K).astype(np.float32)
    B = np.random.rand(K, N).astype(np.float32)
    C_ref = A @ B

    print(f"4×4 weight-stationary systolic array doing {M}×{K}×{N} MatMul\n")

    sa = SystolicArray(K, N)
    print("Input schedule (A[m,k] enters PE[k,0] at cycle m+k):")
    for k in range(K):
        for m in range(M):
            print(f"  A[{m},{k}] = {A[m,k]:.3f}  enters PE[{k},0] at cycle {m+k}")

    print("\n--- Running with trace ---")
    C, total_cycles = sa.run(A, B, trace=True)

    print(f"\nTotal cycles: {total_cycles}")
    print(f"Theoretical = M + K + N - 1 = {M + K + N - 1} useful cycles")
    print(f"\nC computed by systolic:")
    with np.printoptions(precision=3, suppress=True):
        print(C)
    print(f"\nC by NumPy (A @ B):")
    with np.printoptions(precision=3, suppress=True):
        print(C_ref)
    print(f"\nallclose (atol=1e-3): {np.allclose(C, C_ref, atol=1e-3)}")

    print("\n--- Larger test (no trace): 16×16×16 ---")
    M = K = N = 16
    A = np.random.rand(M, K).astype(np.float32)
    B = np.random.rand(K, N).astype(np.float32)
    sa16 = SystolicArray(K, N)
    C, cycles = sa16.run(A, B)
    print(f"  cycles: {cycles}, allclose: {np.allclose(C, A @ B, atol=1e-3)}")


if __name__ == "__main__":
    main()
