# 02_mac_modeling_report.md: Design and Modeling of Multiply-Accumulate (MAC) Unit

본 보고서는 [02_hardware_comp_bench.py](../lab/02_hardware_comp_bench.py) 실습을 바탕으로 작성되었습니다. NPU(Neural Processing Unit)의 가장 핵심적인 산술 연산 유닛인 MAC(Multiply-Accumulate) 유닛의 하드웨어적 동작 원리를 이해하고, 이를 서로 다른 추상화 수준(Abstraction Level)에서 모델링 및 검증하는 기법을 정립하는 것을 목적으로 합니다.

---

## 1. 학습 목표 (Learning Objectives)

* NPU의 가장 작은 최소 계산 단위이자 모든 딥러닝 연산의 기반이 되는 MAC 유닛을 직접 설계하고 하드웨어 제약 사항을 파악합니다.
* 연산 정밀도에 따른 **Accumulator Precision**의 물리적 필요성을 이해합니다.
* 정수형 연산 시 발생하는 **INT8 누적 오버플로우(Overflow)**의 원인을 파악하고 데이터 정합성을 검증합니다.
* 알고리즘 수준의 Python 소프트웨어 모델과 하드웨어 수준의 Verilog RTL 설계를 교차 검증하는 시스템 설계 방법론을 숙달합니다.

---

## 2. MAC 유닛의 본질과 AI 워크로드

MAC 유닛은 하드웨어적으로 다음과 같은 단 하나의 핵심 산술 연산으로 정의됩니다.

$$acc \leftarrow acc + (a \times b)$$

이 단순한 곱셈 후 누산 연산이 하드웨어 평면 위에서 수십억에서 수조 번 이상 반복되면서 현대 딥러닝 알고리즘의 거대한 수학적 연산들을 수행하게 됩니다.

* **벡터 내적 (Dot Product)**: 입력 벡터와 가중치 벡터 간의 원소별 곱 및 총합
* **행렬 곱셈 (Matrix Multiplication)**: 고성능 GEMM 가속의 기본 블록
* **합성곱 (Convolution)**: CNN의 공간적 특징 추출 연산
* **Attention 연산 & Transformer 연산**: 거대 언어 모델(LLM)을 지배하는 핵심 행렬곱

결론적으로, **딥러닝의 거의 모든 계산 아키텍처는 이 고성능 MAC 연산의 밀도 높은 반복**이라고 정의할 수 있습니다.

---

## 3. Accumulator Precision의 필요성 및 에너지 비용 분석

### 3.1 정수형 오버플로우 증명 (INT8 Accumulation Overflow)
입력 데이터와 가중치 타입을 모두 `int8`로 설정하는 저전력 추론 가속기 설계 시, 중간 연산 결과를 누적하는 누산기(Accumulator)의 비트 폭 설계가 매우 중요합니다.

* **실험 조건**: 모든 원소가 `1`인 길이 1,000의 두 정수 벡터를 내적 연산하는 상황
* **하드웨어 오류 구조**: 입력 `int8` $\times$ 가중치 `int8` 연산 결과를 누산기 정밀도까지 `int8`로 고정하면, 부호가 있는 8비트 정수의 최대 표현 범위(+127)를 초과하여 연산 값의 손실 및 반전(Overflow)이 발생합니다.
* **아키텍처적 해결 방안**: 하드웨어 곱셈기 출력 버퍼 뒤에 배치되는 중간 누산 레지스터의 폭을 **`int32`** 또는 최소 `int16`으로 확장 확보하여 부호 확장(Sign Extension)을 보장함으로써 정밀도 저하 없는 완벽한 수치적 정합성을 제공해야 합니다.

### 3.2 하드웨어 연산 정밀도별 에너지 비용 프로필
소스 코드 하드웨어 모델에 내재된 데이터 타입 크기별 단일 MAC 작동 에너지 소비량은 다음과 같이 모델링됩니다.

| 입력/가중치 정밀도 (Input/Weight Type) | 누산기 정밀도 (Accumulator Type) | MAC 연산 단일 에너지 비용 |
| :--- | :--- | :--- |
| **int4** | int16 | **0.08 pJ** |
| **int8** | int16 | **0.18 pJ** |
| **int8** | int32 | **0.20 pJ** |
| **bf16** | fp32 | **1.00 pJ** |
| **fp16** | fp32 | **1.10 pJ** |
| **fp32** | fp32 | **3.70 pJ** |

---

## 4. 상위 NPU 아키텍처 설계 사양과의 연계성

본 설계는 앞서 수행한 최상위 시스템 사양 설계 단계와 유기적으로 긴밀히 연결되어 진행됩니다.

1. **상위 설계 사양 결정**: Target Workload, Defining Feature, DType Selection, PE Array Shape, Dataflow Selection, Clock Frequency, SRAM Size, DRAM Bandwidth를 통해 칩의 거시적인 방향성을 정의했습니다.
2. **연산 엔진 실체화**: 정의된 시스템 정밀도 설정을 바탕으로, 실제 연산 회로의 최소 단위인 MAC 유닛을 알고리즘 관점(Python)과 하드웨어 관점(Verilog RTL)으로 투영하여 구체화합니다.
3. **상위 시스템 통합 확장**: 본 단원에서 검증 완료된 물리적 MAC 유닛을 기반으로 향후 온칩 레지스터, SRAM 버퍼, DRAM 인터페이스를 결합하고, 타일링(Tiling) 및 루프라인 모델(Roofline Analysis)을 재적용하여 하드웨어 전체의 최적화를 이뤄내게 됩니다.

---

## 5. 추상화 수준별 하드웨어 모델링 기법 (Core Concepts)

반도체 설계의 핵심은 **"동일한 수학적 알고리즘을 하드웨어 구현 단계에 맞춰 서로 다른 추상화 레벨로 나누어 검증하는 것"**에 있습니다.

| 추상화 수준 (Abstraction) | 구현 방식 (Implementation) | 주된 설계 목적 (Purpose) |
| :--- | :--- | :--- |
| **알고리즘 수준 (Algorithm)** | Python 클래스 (`MACUnit`) | 연산의 기능 정의 및 정합성, 수학적 비용 분석 |
| **RTL 수준 (Hardware RTL)** | Verilog 모듈 (`mac_unit.v`) | 게이트 수준의 실제 연산 회로 설계 및 합성 구현 |
| **검증 수준 (Verification)** | cocotb 프레임워크 | Python 결과와 Verilog 출력 간의 Cycle-by-Cycle 크로스체크 |
| **파형 수준 (Waveform)** | Surfer 뷰어 (vcd/fsdb) | 시간축 기준 전하 제어, 게이트 지연 및 타이밍 마진 관찰 |

> **핵심 아키텍처 통찰**: 
> **"Python은 '무엇을 계산하는가(What to compute)'를 명시하고, Verilog는 '하드웨어가 매 클럭 사이클마다 어떻게 시간에 따라 계산해 내는가(How hardware computes over time)'를 기술합니다."**

---

## 6. 하드웨어 검증 및 프로토타이핑 흐름 (Design Flow)

물리 반도체 칩이 작동을 완료하기까지 아키텍트가 수행해야 할 전체적인 엔지니어링 파이프라인의 설계 흐름도입니다.

```text
MAC 기본 이론 이해 및 연산기 구조 설계
                 │
                 ▼
Accumulator Precision 및 오버플로우 방지 폭 설계
                 │
                 ▼
Python 기반 구조적 MAC 분석 모델 구현 및 시뮬레이션
                 │
                 ▼
인텐디드 Fail 테스트를 통한 INT8 누적 오버플로우 실측 검증
                 │
                 ▼
Verilog HDL 기반의 동기식 하드웨어 MAC RTL 설계
                 │
                 ▼
cocotb 통합 테스트벤치 빌드 및 기능적 테스트 수행
                 │
                 ▼
Python 시뮬레이션 데이터 ↔ Verilog RTL 출력 간 Cross-check
                 │
                 ▼
Surfer/GTKWave 툴을 통한 내부 신호의 Waveform 지연 분석
                 │
                 ▼
NPU 전체 서브시스템(Memory Tier + Matrix Array) 통합 준비 완료
```

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)

* **실습 소스 코드 (Lab)**:
  * [02_hardware_comp_bench.py](../lab/02_hardware_comp_bench.py): 부호 확장 및 비트 오버플로우 기능적 방지 기법과 Register-SRAM-DRAM 간 3단계 계층 구조 메모리의 트래픽 타이밍 지연 및 pJ 단위 에너지 비용을 검증하는 실습 소스 코드입니다.

### 2. 가속기 설계의 정수 (Hardware Insight)

* 본 단원에서 구체화한 정밀도별 단일 MAC 작동 비용과 레지스터 유닛의 기능 모델은 향후 통합 NPU 아키텍처 시뮬레이터에서 전체 연산 행렬 크기에 곱해져 전체 칩셋의 물리 전력 프로필(mJ)을 결정짓는 절대적 상수가 됩니다. 실리콘 수준의 실제 전하 이동 제어와 전성비 최적화를 달성하기 위해, 본 문서에서 도출된 컴포넌트 데이터 정합성은 상위 아키텍처 탐색의 핵심적인 하드웨어 지표로 작용합니다.
