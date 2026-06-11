"""Week 4-1: Design Space Exploration + Pareto front identification."""
import os
import sys
import warnings
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product

import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path

base_path = Path(__file__).resolve().parent
output_dir = base_path / "results"
output_dir.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings("ignore", category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
_W3 = os.path.join(_HERE, "..", "..", "03_npu_prototyping", "lab")


def _import_local(name: str, path: str):
    spec = spec_from_file_location(name, path)
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cfg_mod = _import_local("npu_config_mod", os.path.join(_W3, "01_npu_architecture_bench.py"))
_sim_mod = _import_local("npu_sim_mod", os.path.join(_W3, "04_npu_simulator_bench.py"))

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
DTYPE_BYTES = _cfg_mod.DTYPE_BYTES
NPU = _sim_mod.NPU


SRAM_SIZES_KB = [1_024, 4_096, 16_384, 65_536]              # 1 MB, 4 MB, 16 MB, 64 MB
PE_SHAPES = [(8, 8), (16, 16), (32, 32), (64, 64)]
DTYPES = ["int8", "fp16", "fp32"]

SWEEP_WORKLOAD = (256, 4096, 4096)  # W3 batched


def measure(cfg: NPUConfig, m: int, k: int, n: int) -> dict:
    rng = np.random.default_rng(0)
    A = rng.integers(-3, 4, (m, k), dtype=np.int8)
    B = rng.integers(-3, 4, (k, n), dtype=np.int8)
    npu = NPU(cfg)
    r = npu.run(A, B)
    latency_s = r.cycles / (cfg.clock_ghz * 1e9)
    return {"latency_ms": latency_s * 1e3, "energy_mj": r.energy_pj / 1e9}


def is_pareto(points: list[tuple[float, float]]) -> list[bool]:
    """Return mask: True = non-dominated. Smaller is better on both axes."""
    n = len(points)
    out = [True] * n
    for i in range(n):
        li, ei = points[i]
        for j in range(n):
            if i == j:
                continue
            lj, ej = points[j]
            if lj <= li and ej <= ei and (lj < li or ej < ei):
                out[i] = False
                break
    return out


def main() -> None:
    base = make_reference_config()
    print(f"=== DSE sweep on workload M×K×N = {SWEEP_WORKLOAD} ===")
    print(f"Sweeping {len(SRAM_SIZES_KB)} SRAM × {len(PE_SHAPES)} PE × {len(DTYPES)} dtype "
          f"= {len(SRAM_SIZES_KB) * len(PE_SHAPES) * len(DTYPES)} configs\n")

    results: list[tuple[NPUConfig, dict]] = []
    for sram_kb, (pe_r, pe_c), dtype in product(SRAM_SIZES_KB, PE_SHAPES, DTYPES):
        cfg = deepcopy(base)
        cfg.name = f"sram{sram_kb//1024}M_pe{pe_r}x{pe_c}_{dtype}"
        cfg.sram_kb = sram_kb
        cfg.pe_array_rows = pe_r
        cfg.pe_array_cols = pe_c
        cfg.dtype = dtype
        cfg.dtype_bytes = DTYPE_BYTES[dtype]
        r = measure(cfg, *SWEEP_WORKLOAD)
        results.append((cfg, r))

    points = [(r["latency_ms"], r["energy_mj"]) for _, r in results]
    pareto_mask = is_pareto(points)
    n_pareto = sum(pareto_mask)
    print(f"Pareto front: {n_pareto} / {len(results)} configs are non-dominated\n")

    print("--- Pareto-front configs (sorted by latency) ---")
    pareto_configs = sorted(
        [(cfg, r) for (cfg, r), p in zip(results, pareto_mask) if p],
        key=lambda x: x[1]["latency_ms"],
    )
    for cfg, r in pareto_configs:
        print(f"  {cfg.name:<30}  {r['latency_ms']:>8.3f} ms   {r['energy_mj']:>8.2f} mJ")

    # Identify base config
    base_idx = next(
        i for i, (cfg, _) in enumerate(results)
        if cfg.sram_kb == base.sram_kb
        and cfg.pe_array_rows == base.pe_array_rows
        and cfg.dtype == base.dtype
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, ((cfg, r), is_p) in enumerate(zip(results, pareto_mask)):
        color = "tab:red" if is_p else "lightgray"
        marker = "o" if cfg.dtype == "int8" else "s" if cfg.dtype == "fp16" else "^"
        size = 90 if is_p else 35
        ax.scatter([r["latency_ms"]], [r["energy_mj"]], c=color, marker=marker, s=size, alpha=0.7)
    base_pt = points[base_idx]
    ax.scatter([base_pt[0]], [base_pt[1]], c="blue", marker="*", s=300, label="base config", zorder=5)
    pareto_pts = sorted(
        [(p[0], p[1]) for p, m in zip(points, pareto_mask) if m],
        key=lambda x: x[0],
    )
    if pareto_pts:
        xs, ys = zip(*pareto_pts)
        ax.plot(xs, ys, "r--", alpha=0.5, label="Pareto front")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Latency (ms, log)")
    ax.set_ylabel("Energy (mJ, log)")
    ax.set_title(f"DSE — {len(results)} configs on W3 (256×4096×4096), markers: ○=int8 □=fp16 △=fp32")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(output_dir / "01_pareto_front.png", dpi=100)
    print("\nSaved: 01_pareto_front.png")

    # Where does base sit?
    base_lat, base_e = base_pt
    print(f"\nBase config: latency={base_lat:.3f} ms, energy={base_e:.2f} mJ")
    print(f"Base on Pareto front: {pareto_mask[base_idx]}")


if __name__ == "__main__":
    main()
