"""Week 3-1: NPU configuration dataclass."""
from dataclasses import dataclass


DTYPE_BYTES = {"int8": 1, "int16": 2, "fp16": 2, "bf16": 2, "fp32": 4}


@dataclass
class NPUConfig:
    name: str
    defining_feature: str
    dtype: str
    dtype_bytes: int
    pe_array_rows: int
    pe_array_cols: int
    dataflow: str            # 'WS', 'OS', 'IS'
    clock_ghz: float
    sram_kb: int
    dram_bw_gbps: float
    target_workload: str

    @property
    def n_pes(self) -> int:
        return self.pe_array_rows * self.pe_array_cols

    @property
    def peak_ops_per_sec(self) -> float:
        # 1 MAC = 2 ops; each PE does 1 MAC per cycle when fully utilized.
        return self.n_pes * 2 * self.clock_ghz * 1e9

    @property
    def peak_tops(self) -> float:
        return self.peak_ops_per_sec / 1e12

    @property
    def sram_bytes(self) -> int:
        return self.sram_kb * 1024

    def summary(self) -> str:
        return (
            f"  name              : {self.name}\n"
            f"  defining feature  : {self.defining_feature}\n"
            f"  dtype             : {self.dtype} ({self.dtype_bytes} bytes)\n"
            f"  PE array          : {self.pe_array_rows}×{self.pe_array_cols} = {self.n_pes} PEs\n"
            f"  dataflow          : {self.dataflow}\n"
            f"  clock             : {self.clock_ghz} GHz\n"
            f"  SRAM              : {self.sram_kb} KB ({self.sram_kb/1024:.1f} MB)\n"
            f"  DRAM BW           : {self.dram_bw_gbps} GB/s\n"
            f"  target workload   : {self.target_workload}\n"
            f"  peak              : {self.peak_tops:.3f} TOPS"
        )


def make_reference_config() -> NPUConfig:
    return NPUConfig(
        name="edu-NPU-v1",
        defining_feature="INT8 + 16MB SRAM, 16×16 systolic for batched inference",
        dtype="int8",
        dtype_bytes=DTYPE_BYTES["int8"],
        pe_array_rows=16,
        pe_array_cols=16,
        dataflow="WS",
        clock_ghz=1.0,
        sram_kb=16_384,
        dram_bw_gbps=200,
        target_workload="LLM batched inference",
    )


def main() -> None:
    cfg = make_reference_config()
    print("=== Reference NPUConfig ===\n")
    print(cfg.summary())
    print()
    print(f"  n_pes               = {cfg.n_pes}")
    print(f"  peak_ops_per_sec    = {cfg.peak_ops_per_sec:,.0f} ops/s")
    print(f"  peak_tops           = {cfg.peak_tops:.3f} TOPS")
    print(f"  sram_bytes          = {cfg.sram_bytes:,}")


if __name__ == "__main__":
    main()
