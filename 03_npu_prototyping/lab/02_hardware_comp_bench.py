"""Week 3-2: MAC unit + 3-tier memory model."""
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)


_DTYPE_NP = {
    "int8": np.int8, "int16": np.int16, "int32": np.int32,
    "fp16": np.float16, "bf16": np.float32,  # bf16 fallback to fp32 for accumulation
    "fp32": np.float32,
}

_MAC_ENERGY_PJ = {
    ("int8", "int32"):  0.20,
    ("int8", "int16"):  0.18,
    ("int4", "int16"):  0.08,
    ("fp16", "fp32"):   1.10,
    ("bf16", "fp32"):   1.00,
    ("fp32", "fp32"):   3.70,
}


class MACUnit:
    """Single MAC: input × weight, accumulated into a (typically larger) accumulator."""

    def __init__(self, input_dtype: str, weight_dtype: str, accum_dtype: str) -> None:
        self.input_dtype = input_dtype
        self.weight_dtype = weight_dtype
        self.accum_dtype = accum_dtype
        self._np_in = _DTYPE_NP[input_dtype]
        self._np_acc = _DTYPE_NP[accum_dtype]
        self._acc = self._np_acc(0)

    def reset(self) -> None:
        self._acc = self._np_acc(0)

    def step(self, input_val, weight_val):
        prod = self._np_acc(self._np_in(input_val)) * self._np_acc(self._np_in(weight_val))
        self._acc = self._np_acc(self._acc + prod)
        return self._acc

    @property
    def output(self):
        return self._acc

    @property
    def per_mac_energy_pj(self) -> float:
        return _MAC_ENERGY_PJ.get((self.input_dtype, self.accum_dtype), 1.0)


class Memory:
    def __init__(
        self,
        name: str,
        size_bytes: int,
        bw_bytes_per_cycle: float,
        latency_cycles: int,
        energy_pj_per_byte: float,
    ) -> None:
        self.name = name
        self.size_bytes = size_bytes
        self.bw_bytes_per_cycle = bw_bytes_per_cycle
        self.latency_cycles = latency_cycles
        self.energy_pj_per_byte = energy_pj_per_byte
        self._reads = 0
        self._writes = 0
        self._energy = 0.0

    def read(self, n_bytes: int) -> tuple[int, float]:
        cycles = self.latency_cycles + int(np.ceil(n_bytes / self.bw_bytes_per_cycle))
        energy = n_bytes * self.energy_pj_per_byte
        self._reads += n_bytes
        self._energy += energy
        return cycles, energy

    def write(self, n_bytes: int) -> tuple[int, float]:
        cycles = self.latency_cycles + int(np.ceil(n_bytes / self.bw_bytes_per_cycle))
        energy = n_bytes * self.energy_pj_per_byte
        self._writes += n_bytes
        self._energy += energy
        return cycles, energy

    @property
    def total_reads(self) -> int:
        return self._reads

    @property
    def total_writes(self) -> int:
        return self._writes

    @property
    def total_energy_pj(self) -> float:
        return self._energy


def test_mac_int8_overflow() -> None:
    print("--- INT8 overflow demonstration (intended failure) ---")
    print("dot product of two length-1000 vectors of all 1s:")
    print(f"  Expected: 1000")

    # Wrong: INT8 input × INT8 weight, INT8 accum (will overflow)
    mac_bad = MACUnit("int8", "int8", "int8")
    for _ in range(1000):
        mac_bad.step(1, 1)
    print(f"  INT8 input × INT8 weight, INT8 accum: {int(mac_bad.output)} (overflowed)")

    # Right: INT8 inputs, INT32 accumulator
    mac_good = MACUnit("int8", "int8", "int32")
    for _ in range(1000):
        mac_good.step(1, 1)
    print(f"  INT8 input × INT8 weight, INT32 accum: {int(mac_good.output)} ✓")


def test_mac_fp_correctness() -> None:
    print("\n--- FP16 input × FP16 weight, FP32 accum (matches NumPy dot) ---")
    rng = np.random.default_rng(0)
    a = rng.uniform(-1, 1, 100).astype(np.float16)
    b = rng.uniform(-1, 1, 100).astype(np.float16)
    expected = float(np.dot(a.astype(np.float32), b.astype(np.float32)))

    mac = MACUnit("fp16", "fp16", "fp32")
    for av, bv in zip(a, b):
        mac.step(float(av), float(bv))
    print(f"  Expected: {expected:.6f}")
    print(f"  MAC:      {float(mac.output):.6f}")
    print(f"  Close:    {abs(expected - float(mac.output)) < 0.1}")


def test_memory_tiers() -> None:
    print("\n--- 3-tier memory model ---")
    sram = Memory(
        name="SRAM",
        size_bytes=16 * 1024 * 1024,
        bw_bytes_per_cycle=64,    # 64 B/cycle ≈ 64 GB/s @ 1 GHz
        latency_cycles=2,
        energy_pj_per_byte=5.0,
    )
    dram = Memory(
        name="DRAM",
        size_bytes=16 * 1024**3,
        bw_bytes_per_cycle=200,   # 200 B/cycle ≈ 200 GB/s @ 1 GHz
        latency_cycles=100,
        energy_pj_per_byte=100.0,
    )

    for n_bytes in (1024, 1024 * 1024, 64 * 1024 * 1024):
        sram_cycles, sram_e = sram.read(n_bytes)
        dram_cycles, dram_e = dram.read(n_bytes)
        print(
            f"  read {n_bytes:>14,} B   SRAM: {sram_cycles:>9,}cy / {sram_e/1e6:>8.3f}μJ"
            f"   DRAM: {dram_cycles:>9,}cy / {dram_e/1e6:>8.3f}μJ"
        )
    print(f"\n  SRAM total reads={sram.total_reads:,}, energy={sram.total_energy_pj/1e9:.3f} mJ")
    print(f"  DRAM total reads={dram.total_reads:,}, energy={dram.total_energy_pj/1e9:.3f} mJ")


def main() -> None:
    test_mac_int8_overflow()
    test_mac_fp_correctness()
    test_memory_tiers()


if __name__ == "__main__":
    main()
