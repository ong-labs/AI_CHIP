# 02_accelerator_architecture: NPU Microarchitecture & Dataflow Design

이 폴더는 범용 연산(General Computing)을 넘어 특화 가속기(Accelerator)의 핵심 설계 원리인 데이터 흐름(Dataflow)과 하드웨어 매핑(Mapping)을 다룹니다. 데이터를 칩 내부에서 어떻게 효율적으로 이동시키고 재사용(Stationary)하여 에너지 효율을 극대화할 것인지에 대한 아키텍처적 통찰을 학습합니다.

---

## 📂 저장소 워크플로우 (A-L-M)

본 저장소는 엔지니어링 표준 사이클을 따라 구성되어 있습니다.

1. **analysis**: 데이터 흐름, 에너지 효율 및 하드웨어 타이밍에 대한 이론적 분석
2. **lab**: 아키텍처 시뮬레이터를 코드로 구현하고 사이클 단위 데이터를 수집하는 실습 단계
3. **mastery**: 수집된 데이터를 해석하고 가속기 설계 지식의 무결성을 검증하는 숙달 단계

---

## 📝 커리큘럼 로드맵

### Unit 1. 행렬곱 데이터 흐름 및 스테이셔너리 분석

행렬곱의 6가지 루프 순서(Ordering)를 분석하여 NPU 설계의 핵심인 OS, IS, WS 데이터 흐름을 분류하고, 메모리 접근 에너지를 최소화하는 전략을 학습합니다.

* **[analysis]** [01_matmul_dataflow_report.md](./analysis/01_matmul_dataflow_report.md): 데이터 재사용 전략 및 Stationary Dataflow 분석
* **[lab]** [01_matmul_loop_map_bench.py](./lab/01_matmul_loop_map_bench.py): 루프 매핑 및 스테이셔너리 분류 벤치마크

### Unit 2. 시스톨릭 어레이 주기 정밀 시뮬레이션

Google TPU의 핵심 구조인 Systolic Array를 사이클 단위로 시뮬레이션하여, 파이프라인의 Fill/Drain 과정과 하드웨어 활용률(Utilization)의 동역학을 정량적으로 분석합니다.

* **[analysis]** [02_systolic_array_report.md](./analysis/02_systolic_array_report.md): Weight-Stationary 시뮬레이션 및 타이밍 분석 보고서
* **[analysis]** [02_systolic_array_scrutiny.md](./analysis/02_systolic_array_scrutiny.md): Systolic Array 동작 방식 세부 분해 및 Wavefront 분석
* **[analysis]** [02_systolic_array_trace.md](./analysis/02_systolic_array_trace.md): NPU 핵심 로직의 하드웨어 매핑 및 설계 사양 분석
* **[lab]** [02_tpu_ws_systolic_bench.py](./lab/02_tpu_ws_systolic_bench.py): Cycle-accurate 가중치 고정형 시스톨릭 어레이 시뮬레이터
* **[mastery]** [02_accelerator_mastery.md](./mastery/02_accelerator_mastery.md): 시스톨릭 어레이 및 데이터 흐름 설계 지식 숙달 검증

---

## 🏗️ Directory Structure

```text
02_accelerator_architecture/
├── README.md
├── analysis/
│   ├── 01_matmul_dataflow_report.md    # 데이터 흐름 및 재사용 전략 분석
│   ├── 02_systolic_array_report.md     # 시스톨릭 어레이 타이밍 분석 보고서
│   ├── 02_systolic_array_scrutiny.md   # 시스톨릭 어레이 동작 방식 세부 분해
│   └── 02_systolic_array_trace.md      # NPU 핵심 로직의 하드웨어 매핑 분석
├── lab/
│   ├── 01_matmul_loop_map_bench.py     # 루프 매핑 및 스테이셔너리 분류 실습
│   └── 02_tpu_ws_systolic_bench.py     # 주기 정밀 시스톨릭 어레이 시뮬레이터
└── mastery/
    └── 02_accelerator_mastery.md       # 가속기 설계 지식 검증 및 숙달
```

---

*본 저장소는 하드웨어 특화 가속기의 정밀한 설계를 추구하며, 모든 시뮬레이션 데이터는 검증되었습니다.*