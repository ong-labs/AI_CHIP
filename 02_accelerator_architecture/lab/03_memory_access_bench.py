"""Week 2-3: WS / OS / IS dataflow memory access counting.

We do NOT cycle-simulate (that was 2-2). Instead, count memory accesses
analytically per dataflow for an M×K×N MatMul on a (PE_R × PE_C) array, with
appropriate tiling. Bytes = (accesses) × dtype_bytes.

Simplifying assumptions:
  - No DRAM caching beyond what the dataflow's reuse pattern provides.
  - For each tile, each input/weight needs to come from DRAM once (no L2/cache prefetch).
  - Output partial sums accumulate inside PE (or scratchpad), only written to DRAM at end.
  - PE-to-PE moves counted per data hop within array.
"""

import warnings
from dataclasses import dataclass

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class DataflowStats:
    name: str
    cycles: int
    dram_read_bytes: int
    dram_write_bytes: int
    pe_moves: int
    C: np.ndarray


def _tiled_loop_count(M: int, K: int, N: int, PE_R: int, PE_C: int) -> tuple[int, int, int]:
    n_tiles_m = (M + PE_R - 1) // PE_R
    n_tiles_n = (N + PE_C - 1) // PE_C
    n_tiles_k = (K + PE_R - 1) // PE_R
    return n_tiles_m, n_tiles_n, n_tiles_k


def simulate(
    A: np.ndarray,
    B: np.ndarray,
    dataflow: str,
    pe_r: int = 4,
    pe_c: int = 4,
    dtype_bytes: int = 4,
) -> DataflowStats:
    """Compute C = A @ B and count memory accesses for the given dataflow.

    dataflow ∈ {'WS', 'OS', 'IS'}.
    """
    M, K = A.shape
    _, N = B.shape
    nt_m, nt_n, nt_k = _tiled_loop_count(M, K, N, pe_r, pe_c)

    # All three produce the same numerical result; differences are only in access counts.
    C = A @ B

    weight_bytes_total = K * N * dtype_bytes
    input_bytes_total = M * K * dtype_bytes
    output_bytes_total = M * N * dtype_bytes

    # Per-tile bytes (one tile of weight, input, partial sum)
    tile_w_bytes = pe_r * pe_c * dtype_bytes
    tile_i_bytes = pe_r * pe_c * dtype_bytes
    tile_o_bytes = pe_r * pe_c * dtype_bytes

    pe_count = pe_r * pe_c

    if dataflow == "WS":
        # Weight stationary: Weight loaded once per (m_tile, n_tile, k_tile);
        # but for inner k accumulation, weight tile changes per k_tile.
        # Reuse: same weight tile reused across M-tiles → weight read = nt_n * nt_k tiles
        # Input streamed through → input read = nt_m * nt_n * nt_k tiles
        # Output written once per (m_tile, n_tile) at end → output_bytes_total
        weight_reads = nt_n * nt_k * tile_w_bytes
        input_reads = nt_m * nt_n * nt_k * tile_i_bytes
        output_writes = output_bytes_total
        # PE moves: each input traverses pe_c PEs in its row per cycle
        pe_moves = nt_m * nt_n * nt_k * pe_count * pe_c
        cycles = nt_m * nt_n * nt_k * (pe_r + pe_c + pe_r - 1)
    elif dataflow == "OS":
        # Output stationary: Partial sum stays in PE until k accumulation done.
        # Weight changes per k_tile → loaded each (m_tile, n_tile, k_tile)
        # Input loaded each (m_tile, n_tile, k_tile) too.
        # Output written once per (m_tile, n_tile)
        weight_reads = nt_m * nt_n * nt_k * tile_w_bytes
        input_reads = nt_m * nt_n * nt_k * tile_i_bytes
        output_writes = output_bytes_total
        pe_moves = nt_m * nt_n * nt_k * pe_count * 2
        cycles = nt_m * nt_n * nt_k * (pe_r + pe_c)
    elif dataflow == "IS":
        # Input stationary: input tile stays in PE; weights and partial sums flow.
        # Input read = nt_m * nt_k tiles (each input tile reused across N-tiles)
        weight_reads = nt_m * nt_n * nt_k * tile_w_bytes
        input_reads = nt_m * nt_k * tile_i_bytes
        output_writes = output_bytes_total
        pe_moves = nt_m * nt_n * nt_k * pe_count * pe_r
        cycles = nt_m * nt_n * nt_k * (pe_r + pe_c + pe_c - 1)
    else:
        raise ValueError(f"Unknown dataflow: {dataflow}")

    return DataflowStats(
        name=dataflow,
        cycles=cycles,
        dram_read_bytes=weight_reads + input_reads,
        dram_write_bytes=output_writes,
        pe_moves=pe_moves,
        C=C,
    )


def compare_dataflows(M: int, K: int, N: int, label: str = "", pe_r: int = 4, pe_c: int = 4) -> None:
    np.random.seed(0)
    A = np.random.rand(M, K).astype(np.float32)
    B = np.random.rand(K, N).astype(np.float32)

    print(f"\n=== {label or f'{M}×{K}×{N}'} on {pe_r}×{pe_c} PE array ===")
    print(f"{'Dataflow':<5} {'cycles':>10} {'DRAM read MB':>14} {'DRAM write MB':>14} {'PE moves':>14}")

    results = {}
    for df in ("WS", "OS", "IS"):
        s = simulate(A, B, df, pe_r, pe_c)
        results[df] = s
        print(
            f"{s.name:<5} {s.cycles:>10,} "
            f"{s.dram_read_bytes/1e6:>14.3f} "
            f"{s.dram_write_bytes/1e6:>14.3f} "
            f"{s.pe_moves:>14,}"
        )

    best_dram = min(results.values(), key=lambda s: s.dram_read_bytes + s.dram_write_bytes)
    print(f"  Lowest DRAM traffic: {best_dram.name}")


def main() -> None:
    print("Comparing 3 dataflows (Weight / Output / Input stationary)")
    print("on a 4×4 PE array for several workloads:\n")

    compare_dataflows(8, 8, 8, "Tiny — fits in one tile per dim")
    compare_dataflows(64, 64, 64, "Mid — N×N MatMul")
    compare_dataflows(256, 4096, 64, "Batched FC layer  (M=256, K=4096, N=64)")
    compare_dataflows(1, 4096, 4096, "Single-batch GEMV (M=1, K=4096, N=4096)")
    compare_dataflows(4096, 4096, 4096, "Large balanced MatMul")


if __name__ == "__main__":
    main()
