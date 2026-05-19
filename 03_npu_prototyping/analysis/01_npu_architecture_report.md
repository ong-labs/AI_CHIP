# 01_npu_architecture_report.md: Defining NPU Architecture & Hardware Parameters

본 보고서는 [01_npu_architecture_bench.py](../lab/01_npu_architecture_bench.py) 소스 코드를 기반으로 작성되었습니다. 우리가 직접 프로토타이핑할 도메인 특화 가속기(DSA)의 핵심 하드웨어 파라미터를 정의하고, 목표 워크로드에 최적화된 아키텍처 사양을 도출하는 것을 목적으로 합니다.

---

## 1. 아키텍처 정의 목표 (Target Goal)

이번 단계에서는 우리가 설계할 NPU의 핵심 아키텍처 파라미터를 정량적으로 정의합니다. 이 NPU가 해결하고자 하는 문제를 명확히 하고, 그 목적에 맞추어 데이터 타입(Data Type), 데이터플로우(Dataflow), PE 배열 크기(PE Array Shape), 클럭 주파수, 그리고 메모리 시스템 용량을 설정합니다.

이 과정은 단순한 하드웨어 변수 설정이 아니라, 다음의 핵심적인 질문에 답을 찾아가는 설계 프로세스입니다.
> **"이 칩은 무엇을 가장 잘 계산하도록 설계할 것인가?"**

---

## 2. 핵심 설계 철학 (Defining Feature)

**Defining Feature**는 이 NPU의 정체성을 한 문장으로 설명하는 핵심 설계 철학입니다.

* **설계 예시**:
    * `INT8 + 16MB SRAM, 16×16 Systolic Array for Batched Inference`
    * `BF16 + HBM, Large GEMM for LLM Training`
    * `INT4 + Low Power for Mobile On-device AI`

이 한 문장은 칩이 사용하는 데이터 타입, 온칩 메모리 용량, PE 배열 구조, 그리고 궁극적으로 달성하려는 목표 워크로드를 모두 규정합니다. 이후의 모든 세부 설계 결정은 이 Defining Feature를 구체화하는 과정이 됩니다.

---

## 3. 세부 하드웨어 파라미터 설계 (Hardware Specs)

### 3.1 데이터 타입 선택 (Data Type Selection)
데이터 타입은 NPU의 연산 정확도, 메모리 대역폭 요구량, 전력 효율, 그리고 동일 면적 대비 최대 처리량(Peak TOPS)에 직접적인 영향을 미칩니다.

| Data Type | Bytes | 주요 용도 |
| :--- | :--- | :--- |
| **INT8** | 1 | 양자화 기반 추론(Inference) 최적화 |
| **INT16** | 2 | 중간 정밀도 정수 연산 |
| **FP16** | 2 | 가속기 범용 딥러닝 학습 및 추론 |
| **BF16** | 2 | 지수부 확장을 통한 대규모 AI 학습/추론 안정성 확보 |
| **FP32** | 4 | 고정밀 과학 계산 및 마스터 가중치 저장 |

* **하드웨어 코드 매핑**:
```python
DTYPE_BYTES = {
    "int8": 1,
    "int16": 2,
    "fp16": 2,
    "bf16": 2,
    "fp32": 4
}
```

### 3.2 PE 배열 구조 (PE Array Shape)

Processing Element(PE)는 곱셈-누적(MAC) 연산을 수행하는 하드웨어의 기본 산술 단위입니다. 이 PE들을 2차원 격자 구조로 배치함으로써 고효율 시스톨릭 어레이(Systolic Array)를 구성합니다.

* **설계 사양**: `pe_array_rows = 16`, `pe_array_cols = 16`
* **총 PE 개수 계산 로직**:

$$\text{n\_pes} = \text{pe\_array\_rows} \times \text{pe\_array\_cols}$$


$$16 \times 16 = 256\text{ PEs}$$


### 3.3 데이터플로우 선택 (Dataflow Selection)

데이터플로우는 어떤 데이터를 온칩 가속기 내부에 최대한 유지(Stationary)하며 재사용할 것인가를 정의하는 핵심 제어 아키텍처입니다.

* **추천 선택 기준**:
* **Large GEMM (대규모 연산)**: 가중치 고정(WS) 또는 출력 고정(OS) 아키텍처
* **Batch-1 GEMV (단일 추론)**: 입력 데이터 고정(IS) 아키텍처
* **General Purpose (범용)**: 제어 로직이 균형 잡힌 출력 고정(OS) 아키텍처


* **설계 핵심 원칙**:
> **"Compute is cheap. Data movement is expensive."** (연산은 저렴하고 데이터 이동은 비싸다)


### 3.4 클럭 주파수 및 시스템 메모리 사양 (Clock & Memory)

* **클럭 주파수**: `clock_ghz = 1.0` (각 PE는 초당 10억 번의 클럭 사이클을 수행합니다.)
* **온칩 SRAM 용량**: `sram_kb = 16_384`
* 바이트 변환: $\text{sram\_bytes} = \text{sram\_kb} \times 1024$
* $\text{결론}: 16,384\text{ KB} = 16\text{ MB}$ 온칩 버퍼 확보


* **DRAM 대역폭**: `dram_bw_gbps = 200` (외부 메모리로부터 초당 최대 200 GB의 연산 데이터를 공급합니다.)
* **목표 워크로드**: `target_workload = "LLM batched inference"`

---

## 4. 이론적 피크 성능 모델링 (Peak Performance Model)

각 PE가 매 사이클마다 1개의 MAC(Multiply-Accumulate) 연산을 유효하게 수행한다고 가정할 때, 1 MAC은 2 부동소수점 연산(Multiply + Add)으로 환산됩니다.

* **이론적 Peak 성능 산출 식**:

$$\text{Peak Ops/s} = N_{PE} \times 2 \times \text{Clock Frequency}$$


* **수치 계산 예시**:

$$256\text{ PEs} \times 2 \times 1\text{ GHz} = 512\text{ GOPS} = 0.512\text{ TOPS}$$


* **성능 평가 소스 코드**:

```python
@property
def peak_ops_per_sec(self) -> float:
    return self.n_pes * 2 * self.clock_ghz * 1e9

@property
def peak_tops(self) -> float:
    return self.peak_ops_per_sec / 1e12
```

---

## 5. 아키텍처 통합 구조체 및 레퍼런스 사양

### 5.1 `NPUConfig` 데이터 클래스

칩의 모든 핵심 파라미터를 단일 객체 구조체로 통합하여 NPU 마이크로아키텍처 사양을 명확히 명시합니다.

```python
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
```

또한, 객체의 사양을 한눈에 요약 출력해 주는 `summary()` 메서드를 구현하여 하드웨어 제원 리포팅 도구를 마련했습니다.

### 5.2 레퍼런스 하드웨어 구성 (`edu-NPU-v1`)

구현된 사양을 기반으로 정립한 첫 번째 교육용 레퍼런스 가속기 프로필입니다.

```python
NPUConfig(
    name="edu-NPU-v1",
    defining_feature="INT8 + 16MB SRAM, 16×16 systolic for batched inference",
    dtype="int8",
    dtype_bytes=1,
    pe_array_rows=16,
    pe_array_cols=16,
    dataflow="WS",
    clock_ghz=1.0,
    sram_kb=16_384,
    dram_bw_gbps=200,
    target_workload="LLM batched inference"
)
```

---

## 6. 아키텍처 컴파일 및 분석 플로우 (Block Diagram)

본 프로젝트의 마이크로아키텍처 설계와 정량적 성능 평가 흐름은 아래와 같은 위계에 따라 상호 유기적으로 진행됩니다.

```text
Target Workload (해결 대상 작업 정의)
      │
      ▼
Defining Feature (NPU 핵심 설계 아키텍처 철학 수립)
      │
      ▼
DType Selection (데이터 타입 및 정밀도 바이트 폭 결정)
      │
      ▼
PE Array Shape (연산 평면의 행/열 및 물리 PE 개수 확정)
      │
      ▼
Dataflow Selection (온칩 데이터 라우팅 및 Stationary 제어 패턴 선택)
      │
      ▼
Clock / SRAM / DRAM BW (동작 주파수 및 시스템 메모리 인터페이스 통합)
      │
      ▼
NPUConfig Dataclass (종합 하드웨어 파라미터 구조체 명세화)
      │
      ▼
Peak TOPS & Roofline Analysis (피크 가용 성능 모델링 및 병목 지점 예측 평가)
```

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)

* **세부 아키텍처 탐색 분석 (Analysis)**: '6. 아키텍처 컴파일 및 분석 플로우'에 정의된 블록 다이어그램의 각 단계별 설계 의사결정 기준과 상호 인과관계에 대한 심층적인 개념 해설은 [01_block_diagram_scrutiny.md](./01_block_diagram_scrutiny.md) 문서에서 상세히 확인하실 수 있습니다.
* **실습 소스 코드 (Lab)**: 구조체 기반의 하드웨어 사양 정의 및 이론적 Peak TOPS 자동 산출 엔진의 실제 파이썬 소스 코드는 [01_npu_architecture_bench.py](../lab/01_npu_architecture_bench.py)에 명시되어 있습니다.
* **지식 검증 및 숙달 (Mastery)**: [01_npu_spec_assessment.md](../mastery/01_npu_spec_assessment.md) 에서 워크로드 정의부터 아키텍처 하드웨어 변수 선택, 루프라인 병목 판단 논리 및 성능 계산 산출식을 종합 점검하는 20문항의 개념 숙달 확인 문제집입니다.

### 2. 가속기 설계의 정수 (Hardware Insight)

* 본 보고서에서 확정한 교육용 레퍼런스 가속기 규격(`edu-NPU-v1`)의 하드웨어 스펙은 단순한 정적 변수가 아닙니다. 이는 차후 진행될 마이크로아키텍처 프로토타이핑 과정에서 핵심 연산 가속 엔진이 될 MAC(Multiply-Accumulate) 유닛의 연산 정밀도를 하드웨어적으로 구체화하고, 3단계 구조 메모리 계층(Register-SRAM-DRAM)의 물리적인 사이클 지연 시간 및 에너지 모델을 확립하는 가장 핵심적인 설계 스펙 시트(Spec Sheet)로 작용합니다.
