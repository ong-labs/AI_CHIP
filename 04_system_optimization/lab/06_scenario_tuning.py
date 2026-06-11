"""Week 4-6: tune NPU for LLM chatbot, measure regression on other apps."""
import os
import sys
import warnings
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location

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
_app_mod = _import_local("app_workload_mod", os.path.join(_HERE, "04_app_workload.py"))

NPUConfig = _cfg_mod.NPUConfig
make_reference_config = _cfg_mod.make_reference_config
NPU = _sim_mod.NPU
measure_autonomous = _app_mod.measure_autonomous
measure_llm_chat = _app_mod.measure_llm_chat
measure_video = _app_mod.measure_video


def measure_all_apps(cfg: NPUConfig) -> dict:
    npu = NPU(cfg)
    return {
        "autonomous": measure_autonomous(npu),
        "llm_chat": measure_llm_chat(npu),
        "video": measure_video(npu),
    }


def main() -> None:
    base_cfg = make_reference_config()
    print("=== Step 1: base config (edu-NPU-v1) on 3 applications ===")
    print(base_cfg.summary())
    base = measure_all_apps(base_cfg)

    target_app = "llm_chat"
    print(f"\nTarget application: {target_app} (priority: {base[target_app]['priority_metric']})")

    # Step 2: tune for LLM chatbot
    # Strategy: The chatbot prefill is large batched matmul (256×4096×4096) — already at 1.0 util.
    # Decode is tiny (256×4096×1) → very memory-bound (KV cache lookup pattern).
    # Tuning: larger SRAM (cache full weight) + 32×32 PE (faster prefill) + retain INT8.
    # Cost: more die area + more energy on small workloads (autonomous frame, video).

    tuned_cfg = deepcopy(base_cfg)
    tuned_cfg.name = "edu-NPU-chat (32×32 + 64MB SRAM)"
    tuned_cfg.pe_array_rows = 32
    tuned_cfg.pe_array_cols = 32
    tuned_cfg.sram_kb = 65_536  # 64 MB — fits a 4096×4096 INT8 weight matrix
    tuned_cfg.target_workload = "LLM batched inference (tuned)"
    tuned_cfg.defining_feature = (
        "32×32 INT8 + 64MB SRAM, prefill+decode optimized"
    )

    print(f"\n=== Step 2: tuned config ===")
    print(tuned_cfg.summary())

    tuned = measure_all_apps(tuned_cfg)

    print("\n=== Step 3: before / after on each application ===")
    print(
        f"{'application':<14} {'metric':<20} {'base':>12} {'tuned':>12} {'Δ%':>10} {'direction':>14}"
    )
    print("-" * 90)

    target_pct = 0.0
    other_changes = []
    for app, b, t in [
        ("autonomous", base["autonomous"], tuned["autonomous"]),
        ("llm_chat",   base["llm_chat"],   tuned["llm_chat"]),
        ("video",      base["video"],      tuned["video"]),
    ]:
        metric = b["priority_metric"]
        is_smaller_better = metric == "frame latency (ms)"
        bv = b["priority_value"]
        tv = t["priority_value"]
        if is_smaller_better:
            pct = (tv - bv) / bv * 100
            improved = pct < 0
        else:
            pct = (tv - bv) / bv * 100
            improved = pct > 0
        direction = "↑ better" if improved else "↓ worse" if abs(pct) > 0.5 else "= same"
        marker = "← target" if app == target_app else ""
        print(
            f"{app:<14} {metric:<20} {bv:>12.3f} {tv:>12.3f} {pct:>+9.1f}% {direction:>14} {marker}"
        )
        if app == target_app:
            target_pct = pct if not is_smaller_better else -pct
        else:
            other_pct = pct if not is_smaller_better else -pct
            other_changes.append((app, other_pct))

    # Step 4: specialization analysis
    print("\n=== Step 4: specialization analysis ===")
    target_metric_change = abs(target_pct)
    if target_pct > 0:
        print(f"  Target gain on {target_app}: +{target_metric_change:.1f}% (priority metric improved)")
    else:
        print(f"  Target on {target_app}: {target_pct:.1f}% (priority did NOT improve — re-tune)")
        return

    regressions = [(app, p) for app, p in other_changes if p < -0.5]
    improvements_other = [(app, p) for app, p in other_changes if p >= -0.5]

    if regressions:
        worst_app, worst_pct = min(regressions, key=lambda x: x[1])
        eff = target_metric_change / abs(worst_pct)
        print(f"  Worst regression: {worst_app} priority {worst_pct:+.1f}%")
        print(f"  specialization_efficiency = {eff:.2f}")
        if eff >= 2.0:
            print(f"    ✓ EFFICIENT specialization (gain ≥ 2× cost)")
        elif eff >= 1.0:
            print(f"    ~ MARGINAL specialization (gain barely exceeds cost)")
        else:
            print(f"    ✗ INEFFICIENT — net loss; reconsider tuning")
    else:
        # cost manifests in die area / energy, not metric
        print(f"  No metric regression on other apps.")
        n_pe_ratio = tuned_cfg.n_pes / base_cfg.n_pes
        sram_ratio = tuned_cfg.sram_kb / base_cfg.sram_kb
        print(f"  Cost is hidden — die area grew ~{n_pe_ratio:.1f}× (PE) + ~{sram_ratio:.1f}× (SRAM).")
        print(f"  True cost evaluation must include die area, not just app priority metric.")

    # Bar chart
    apps = ["autonomous", "llm_chat", "video"]
    base_vals = [base[a]["priority_value"] for a in apps]
    tuned_vals = [tuned[a]["priority_value"] for a in apps]
    metrics = [base[a]["priority_metric"] for a in apps]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(apps))
    w = 0.35
    ax.bar(x - w / 2, base_vals, w, label="base", color="lightblue")
    ax.bar(x + w / 2, tuned_vals, w, label="tuned", color="tab:red")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a}\n({m})" for a, m in zip(apps, metrics)])
    ax.set_yscale("log")
    ax.set_ylabel("Priority metric value (log)")
    ax.set_title("Application priority metric: base vs tuned for chatbot")
    ax.legend()
    ax.grid(True, axis="y", which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "05_scenario_tuning.png", dpi=100)
    print("\nSaved: 05_scenario_tuning.png")


if __name__ == "__main__":
    main()
