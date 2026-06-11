"""Week 3-6: bottleneck analysis + 1 design change + before/after comparison."""
import os
import sys
import warnings
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _import_local(name: str, filename: str):
    spec = spec_from_file_location(name, os.path.join(_HERE, filename))
    mod = module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cfg_mod = _import_local("npu_config_mod", "01_npu_architecture_bench.py")
_sim_mod = _import_local("npu_sim_mod", "04_npu_simulator_bench.py")
_perf_mod = _import_local("npu_perf_mod", "05_npu_roofline_bench.py")

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
NPU = _sim_mod.NPU
WORKLOADS = _perf_mod.WORKLOADS
measure_npu = _perf_mod.measure_npu


def diagnose(npu: NPU, m: int, k: int, n: int, r: dict) -> str:
    """Return brief diagnosis: 'compute' | 'memory' | 'underutilized' | 'balanced'."""
    if r["pe_util"] < 0.5:
        return "underutilized"
    flops = 2 * m * k * n
    cfg = npu.config
    bytes_total = (m * k + k * n + m * n) * cfg.dtype_bytes
    ai = flops / bytes_total
    critical_ai = cfg.peak_tops * 1e12 / (cfg.dram_bw_gbps * 1e9)
    if ai < critical_ai * 0.5:
        return "memory"
    if ai > critical_ai * 2:
        return "compute"
    return "balanced"


def main() -> None:
    base_cfg = make_reference_config()
    base_npu = NPU(base_cfg)

    print("=== Step 1: measure base config across all workloads ===\n")
    print(base_cfg.summary())
    base_results = {}
    print(
        f"\n{'Workload':<22} {'lat (ms)':>10} {'TOPS':>8} "
        f"{'DRAM MB':>10} {'pe_util':>9} {'diagnosis':>14}"
    )
    print("-" * 80)
    for wname, m, k, n in WORKLOADS:
        r = measure_npu(base_npu, m, k, n)
        base_results[wname] = r
        diag = diagnose(base_npu, m, k, n, r)
        r["diagnosis"] = diag
        print(
            f"{wname:<22} {r['latency_ms']:>10.4f} {r['tops_measured']:>8.3f} "
            f"{r['dram_read_mb']:>10.2f} {r['pe_util']:>9.3f} {diag:>14}"
        )

    # Step 2: pick a target with high latency that will benefit from more PEs
    target_wname = "W3 LLM batched"
    print(f"\n\n=== Step 2: target workload = {target_wname} ===")
    print(f"  Diagnosis: {base_results[target_wname]['diagnosis']}")
    print(f"  Hypothesis: W3 is compute-bound at 1.0 utilization. More PEs → linear latency drop.")
    print(f"  Approach: 16×16 → 32×32 PE array (4× peak TOPS, ~4× die area, 4× MAC energy/cycle).")
    print(f"  Cost: small workloads (W1) become MORE underutilized; latency/energy on tiny tasks worsens.")

    # Step 3: apply change — quadruple PE array (16x16 -> 32x32)
    tuned_cfg = deepcopy(base_cfg)
    tuned_cfg.name = "edu-NPU-v2 (32×32 PE)"
    tuned_cfg.pe_array_rows = 32
    tuned_cfg.pe_array_cols = 32
    tuned_cfg.defining_feature = base_cfg.defining_feature + " (v2: 32×32 PE for higher peak)"
    tuned_npu = NPU(tuned_cfg)

    print(f"\n=== Step 3: tuned config ===")
    print(tuned_cfg.summary())

    # Step 4: re-measure and compare
    print("\n\n=== Step 4: before / after comparison ===")
    print(
        f"{'Workload':<22} {'lat base':>10} {'lat tuned':>11} "
        f"{'Δ%':>8} {'DRAM base':>11} {'DRAM tuned':>12} {'Δ%':>8} {'note':>12}"
    )
    print("-" * 110)
    target_change_pct = None
    other_changes_pct = []
    for wname, m, k, n in WORKLOADS:
        rb = base_results[wname]
        rt = measure_npu(tuned_npu, m, k, n)
        dlat = (rt["latency_ms"] - rb["latency_ms"]) / rb["latency_ms"] * 100
        ddram = (
            (rt["dram_read_mb"] - rb["dram_read_mb"]) / max(rb["dram_read_mb"], 1e-9) * 100
        )
        is_target = wname == target_wname
        marker = "← target" if is_target else ""
        print(
            f"{wname:<22} {rb['latency_ms']:>10.4f} {rt['latency_ms']:>11.4f} "
            f"{dlat:>+7.1f}% {rb['dram_read_mb']:>11.2f} {rt['dram_read_mb']:>12.2f} "
            f"{ddram:>+7.1f}% {marker:>12}"
        )
        if is_target:
            target_change_pct = dlat
        else:
            other_changes_pct.append(dlat)

    print("\n=== Trade-off analysis ===")
    print(f"  Target ({target_wname}) latency change: {target_change_pct:+.1f}%")
    peak_ratio = tuned_cfg.peak_tops / base_cfg.peak_tops
    pe_ratio = tuned_cfg.n_pes / base_cfg.n_pes
    print(f"  Peak TOPS:  {base_cfg.peak_tops:.3f} → {tuned_cfg.peak_tops:.3f}  ({peak_ratio:.1f}× scale)")
    print(f"  PE count:   {base_cfg.n_pes} → {tuned_cfg.n_pes}  (~{pe_ratio:.1f}× die area, ~{pe_ratio:.1f}× MAC energy/cycle)")
    if target_change_pct < 0:
        per_area_gain = abs(target_change_pct) / pe_ratio
        print(f"  Per-die-area improvement on target: {per_area_gain:.1f}% (vs ideal {abs(target_change_pct)/peak_ratio:.0f}%)")
        if pe_ratio > abs(target_change_pct) / 100:
            print(f"  ⚠ Area grew {pe_ratio:.1f}× but target only improved by {abs(target_change_pct):.0f}%. ")
            print(f"    Consider alternatives: higher clock, smaller dtype, or specialized dataflow.")
        else:
            print(f"  ✓ Linear scaling — gains roughly match resource investment.")
    workloads_helped = sum(1 for x in other_changes_pct if x < -1)
    workloads_hurt = sum(1 for x in other_changes_pct if x > 1)
    print(f"\n  Other workloads helped: {workloads_helped} / hurt: {workloads_hurt}")
    if workloads_hurt == 0:
        print(f"  Note: scaling-up (more PEs) helps everyone; this is NOT specialization.")
        print(f"  True specialization (tuning that helps target but HURTS others) requires")
        print(f"  changing dtype, dataflow, or PE shape — not just count.")


if __name__ == "__main__":
    main()
