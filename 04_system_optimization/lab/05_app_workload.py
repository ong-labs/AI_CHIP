"""Week 4-5: 3 application workloads (auto / chatbot / video) measured on NPU."""
import os
import sys
import warnings
from importlib.util import module_from_spec, spec_from_file_location

import numpy as np

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
NPU = _sim_mod.NPU


def workload_autonomous() -> list[tuple[int, int, int]]:
    """ResNet-style sequence, batch=1 (frame-by-frame perception)."""
    return [
        (1, 2048, 2048),
        (1, 2048, 2048),
        (1, 2048, 1024),
        (1, 1024, 512),
        (1, 512, 1000),
    ]


def workload_llm_chat(batch: int = 256, hidden: int = 4096, decode_steps: int = 100) -> dict:
    return {
        "prefill": (batch, hidden, hidden),
        "decode_per_step": (batch, hidden, 1),
        "decode_steps": decode_steps,
        "tokens_per_call": batch * decode_steps,
    }


def workload_video_edge() -> list[tuple[int, int, int]]:
    """MobileNet-class small GEMM sequence, batch=1."""
    return [(1, 256, 256)] * 20 + [(1, 256, 1000)]


def run_sequence(npu: NPU, layers: list[tuple[int, int, int]]) -> dict:
    rng = np.random.default_rng(0)
    total_cycles = 0
    total_energy = 0.0
    total_dram = 0
    flops = 0
    for m, k, n in layers:
        A = rng.integers(-3, 4, (m, k), dtype=np.int8)
        B = rng.integers(-3, 4, (k, n), dtype=np.int8)
        r = npu.run(A, B)
        total_cycles += r.cycles
        total_energy += r.energy_pj
        total_dram += r.dram_read_bytes + r.dram_write_bytes
        flops += 2 * m * k * n
    latency_s = total_cycles / (npu.config.clock_ghz * 1e9)
    return {
        "total_cycles": total_cycles,
        "latency_ms": latency_s * 1e3,
        "energy_mj": total_energy / 1e9,
        "dram_mb": total_dram / 1e6,
        "tops_avg": flops / latency_s / 1e12,
    }


def measure_autonomous(npu: NPU) -> dict:
    layers = workload_autonomous()
    r = run_sequence(npu, layers)
    r["priority_metric"] = "frame latency (ms)"
    r["priority_value"] = r["latency_ms"]
    r["priority_target"] = "<= 33 ms (30 fps)"
    return r


def measure_llm_chat(npu: NPU) -> dict:
    spec = workload_llm_chat()
    rng = np.random.default_rng(0)
    pm, pk, pn = spec["prefill"]
    A = rng.integers(-3, 4, (pm, pk), dtype=np.int8)
    B = rng.integers(-3, 4, (pk, pn), dtype=np.int8)
    rp = npu.run(A, B)

    dm, dk, dn = spec["decode_per_step"]
    A = rng.integers(-3, 4, (dm, dk), dtype=np.int8)
    B = rng.integers(-3, 4, (dk, dn), dtype=np.int8)
    rd = npu.run(A, B)

    cycles_total = rp.cycles + rd.cycles * spec["decode_steps"]
    energy_total = rp.energy_pj + rd.energy_pj * spec["decode_steps"]
    latency_s = cycles_total / (npu.config.clock_ghz * 1e9)
    tokens = spec["tokens_per_call"]
    return {
        "total_cycles": cycles_total,
        "latency_ms": latency_s * 1e3,
        "energy_mj": energy_total / 1e9,
        "tokens_per_sec": tokens / latency_s,
        "priority_metric": "tokens/sec",
        "priority_value": tokens / latency_s,
        "priority_target": "as high as possible",
    }


def measure_video(npu: NPU) -> dict:
    layers = workload_video_edge()
    r = run_sequence(npu, layers)
    power_w_active = r["energy_mj"] * 1e-3 / (r["latency_ms"] * 1e-3) if r["latency_ms"] > 0 else 0
    r["tops_per_w"] = r["tops_avg"] / max(power_w_active, 1e-6)
    r["priority_metric"] = "TOPS/W"
    r["priority_value"] = r["tops_per_w"]
    r["priority_target"] = "as high as possible (edge: <= 5W envelope)"
    return r


def main() -> None:
    cfg = make_reference_config()
    npu = NPU(cfg)
    print(f"=== Running 3 application workloads on {cfg.name} ===")
    print(cfg.summary())

    auto = measure_autonomous(npu)
    print("\n--- 1. 자율주행 (perception sequence, batch=1) ---")
    print(f"  layers: {workload_autonomous()}")
    print(f"  frame latency:  {auto['latency_ms']:.3f} ms  (target: {auto['priority_target']})")
    print(f"  TOPS avg:       {auto['tops_avg']:.4f}")
    print(f"  energy/frame:   {auto['energy_mj']:.3f} mJ")

    chat = measure_llm_chat(npu)
    print("\n--- 2. LLM 챗봇 (prefill + 100 decode steps, batch=256) ---")
    print(f"  total latency:  {chat['latency_ms']:.3f} ms")
    print(f"  tokens/sec:     {chat['priority_value']:.1f}  ({chat['priority_target']})")
    print(f"  energy total:   {chat['energy_mj']:.3f} mJ")

    video = measure_video(npu)
    print("\n--- 3. 영상처리 엣지 (MobileNet-class, batch=1) ---")
    print(f"  total latency:  {video['latency_ms']:.3f} ms")
    print(f"  TOPS avg:       {video['tops_avg']:.4f}")
    print(f"  TOPS/W:         {video['priority_value']:.4f}  ({video['priority_target']})")
    print(f"  energy total:   {video['energy_mj']:.3f} mJ")

    print("\n=== Application fit summary ===")
    print(f"{'app':<28} {'priority metric':<20} {'value':>12}")
    print("-" * 65)
    print(f"{'1. 자율주행':<25} {auto['priority_metric']:<20} {auto['priority_value']:>12.3f}")
    print(f"{'2. LLM 챗봇':<25} {chat['priority_metric']:<20} {chat['priority_value']:>12.1f}")
    print(f"{'3. 영상 엣지':<25} {video['priority_metric']:<20} {video['priority_value']:>12.4f}")
    print(f"\nDefining feature: {cfg.defining_feature}")
    print(f"Best fit: LLM 챗봇 (designed-for case). 4-4 will tune for this app.")


if __name__ == "__main__":
    main()
