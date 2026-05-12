# 05_hw_architecture_comp.md: CPU vs GPU vs NPU Deep Dive

본 문서는 Unit 05: CPU/GPU/NPU 비교 분석을 다루며, [05_hw_architecture_bench.py](../lab/05_hw_architecture_bench.py) 실습 코드에 구현된 확장된 Roofline 모델의 논리적 기반을 정의합니다. 정밀도(Precision)와 특화 데이터 흐름이 성능에 미치는 영향을 정량적으로 분석하고, 시뮬레이션 파라미터를 통해 AI 반도체 설계의 본질인 '특화(Specialization)'의 가치를 정의합니다.

> **🚀 실측 데이터 검증**: 본 문서에서 다루는 NPU 파라미터(Precision multiplier, Specialized Dataflow)와 확장된 Roofline 이론이 실제 **NVIDIA H100** 및 **Apple Neural Engine** 환경에서 어떻게 성능 가속을 예측하는지는 [05_hw_architecture_report.md](./05_hw_architecture_report.md) 실측 보고서에서 확인하실 수 있습니다.

---

## 1. 앞선 학습과의 연결 (Roadmap)

본 저장소의 학습 흐름은 성능 차이의 관찰에서 시작하여 하드웨어 아키텍처의 통합 모델 구축으로 이어집니다.

* **관찰**: Python Loop vs NumPy 간의 ~700배 성능 격차 확인
* **부분 설명**: 캐시 지역성(Locality)에 따른 3~5배 가속 원리 분석
* **Unit 1-3 (분해)**: SIMD와 인터프리터 오버헤드 제거를 통한 100배 이상의 가속 요인 정량 분해
* **Unit 1-4 (통합)**: Roofline 모델 하나로 CPU와 GPU의 성능을 동일한 수식으로 예측
* **Unit 1-5 (확장)**: 동일 프레임워크에 NPU 파라미터를 추가하여 AI 특화 가속기의 본질 분석

---

## 2. NPU 이론: 왜 GPU로 부족했나?

### 2.1 하드웨어별 정성적 차이 분석

| 축 | CPU | GPU | NPU |
| --- | --- | --- | --- |
| **설계 우선순위** | Latency, 범용성 | Throughput, 그래픽 + 범용 병렬 | **AI 한 워크로드만** |
| **Lane 폭** | 4 ~ 16 | 32 ~ 수천 (Warp × SM) | **수백 ~ 수만 (Systolic)** |
| **정밀도** | FP64 / FP32 | FP32 / FP16 (최신 FP8) | **INT8 / INT4 / FP16 / BF16** |
| **메모리 구조** | 다단 캐시 (자동 관리) | L1/L2 + 거대한 Register | **On-chip SRAM Scratchpad (수동)** |
| **제어 흐름** | 매우 자유로움 | Warp Divergence 페널티 존재 | **매우 제한적** |
| **효율 (TOPS/W)** | 낮음 | 중간 | **매우 높음** |

### 2.2 NPU가 빠른 진짜 이유 (4대 핵심 요인)

1. **낮은 정밀도 (Low Precision)**:
* INT8은 FP32 대비 동일 면적에서 4배의 Lane 밀도와 Throughput을 가집니다.
* 정밀도를 낮출수록 산술 연산 밀도(AI)의 임계점이 낮아져 연산기 집적도가 비약적으로 상승합니다.


2. **연산 패턴 고정 (Fixed Patterns)**:
* AI 연산의 90% 이상인 MatMul/Conv에 최적화된 전용 데이터 경로(예: Systolic Array)를 가집니다.


3. **데이터 이동 통제 (Controlled Movement)**:
* GPU 캐시가 블랙박스라면, NPU의 Scratchpad 메모리는 소프트웨어(컴파일러)가 명시적으로 관리하여 의도된 데이터 재사용(Reuse)을 100% 보장합니다.


4. **고정 데이터 흐름 (Fixed Dataflow)**:
* Weight Stationary 등 특화된 흐름을 통해 데이터를 한 번 가져오면 소모될 때까지 내부에서 최대한 재사용합니다.



---

## 3. 하드웨어 스펙 및 정밀도 밀도

### 3.1 정밀도에 따른 Lane 밀도 (FP32 기준)

| dtype | FP32 대비 lane 밀도 | 주 용도 |
| --- | --- | --- |
| **FP32** | $1\times$ | 모델 학습 (Training) |
| **BF16 / FP16** | $2\times$ | 학습 및 추론 균형 |
| **INT8** | $4\times$ | 추론 (양자화 모델) |
| **INT4 / FP4** | $8\times$ | 거대언어모델(LLM) 추론 가속 |

### 3.2 주요 NPU/가속기 스펙 예시

| 칩 명칭 | Peak Performance | BW | 비고 |
| --- | --- | --- | --- |
| **Google TPU v4** | 275 TFLOPS BF16 | 1.2 TB/s HBM | Cloud-scale, Systolic Array |
| **NVIDIA H100 Tensor Core** | 989 TFLOPS FP16 | 3.35 TB/s | GPU 내부의 NPU와 같은 유닛 |
| **Apple Neural Engine (M2)** | ~15.8 TOPS INT8 | 100 GB/s (공유) | On-device AI 가속기 |
| **Tesla D1 (Dojo)** | 362 TFLOPS BF16 | ~10 TB/s (on-chip) | Wafer-scale 전용 가속기 |

---

## 4. Roofline 모델 확장: NPU 파라미터 추가

본 실습에서는 `roofline_estimate` 함수를 확장하여 다음 파라미터를 추가 적용합니다.

* **dtype**: 연산 정밀도 설정 ('fp32', 'fp16', 'int8', 'bf16')
* **precision_multiplier**: 정밀도에 따른 하드웨어 가속 배율 적용 ($FP32=1, FP16=2, INT8=4, INT4=8$)

### 분석 시 주의사항 (Traps)

* **단위 혼동**: INT8은 **TOPS**, 부동소수점은 **TFLOPS**를 사용하므로 계산 시 `ops/sec`로 단위를 통일해야 합니다.
* **메모리 대역폭의 의미**: 같은 $100\text{ GB/s}$ 대역폭이라도 $INT8$(1 byte/elem)은 $FP32$(4 bytes/elem)보다 초당 4배 더 많은 원소를 전송할 수 있습니다. 
&emsp;&emsp;정밀도($Precision$)에 따른 유효 대역폭 활용률은 다음과 같습니다.

$$Effective\ Element\ BW = \frac{Peak\ BW\ (Bytes/s)}{Bytes\ per\ Element}$$
* **Apple NE 분석**: INT8 연산력인 TOPS 수치만 보면 RTX 4090보다 빠르게 측정될 수 있으나, 이는 정밀도 차이에 따른 결과임을 명확히 인지해야 합니다.

---

## 5. RTL 미리보기: 하드웨어 구현의 기초 (Preview)

지금까지의 분석이 Python을 이용한 추상적 모델링이었다면, 다음 단계에서는 실제 하드웨어 레벨의 연산 블록을 설계합니다.

### 단일 MAC (Multiply-Accumulate) 모듈

NPU의 가장 핵심적인 연산 단위인 MAC을 Verilog로 표현하면 다음과 같습니다.

```verilog
// 단일 MAC 모듈 구현
module mac (
    input  wire                clk,
    input  wire                rst,
    input  wire signed  [7:0]  in_data,
    input  wire signed  [7:0]  weight,
    output reg  signed  [31:0] acc
);
    always @(posedge clk) begin
        if (rst) 
            acc <= 32'sd0;
        else     
            acc <= acc + (in_data * weight);
    end
endmodule
```

이 MAC 유닛들을 2차원으로 배열하여 데이터 흐름을 최적화한 것이 바로 Systolic Array의 기초가 됩니다.

---

## 6. 핵심 메시지 및 정리

### 🎯 오늘의 Insight

1. **NPU의 본질**: NPU는 단순히 Lane이 더 많은 GPU가 아닙니다. **AI라는 특정 워크로드**에 최적화하여 정밀도, 데이터 흐름, 메모리 접근을 극한으로 특화한 칩입니다.
2. **일반화된 모델**: Roofline 식 하나로 CPU, GPU를 넘어 NPU와 TPU까지 동일한 선상에서 분석하고 예측할 수 있습니다.
3. **Memory Wall (메모리 벽)**: 연산기 성능의 발전 속도를 메모리 대역폭이 따라가지 못하는 'Memory Wall' 문제가 현대 AI 반도체 설계의 최대 난제임을 확인했습니다.

### 📝 전체 요약

* **분해 사고**: 성능의 격차는 단일 원인이 아닌 여러 가속 요인의 곱셈으로 결정됩니다.
* **측정 우선주의**: 하드웨어 공식은 기준점일 뿐, 실제 활용률(Utilization)이 진정한 성능입니다.
* **통합의 힘**: 복잡해 보이는 하드웨어 경쟁도 결국 연산 성능(Peak GFLOPS)과 데이터 전송(BW)이라는 두 축의 균형 문제로 귀결됩니다.

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: NPU 파라미터를 수식에 대입하여 5종의 하드웨어를 시뮬레이션하고 시각화 차트를 생성하는 코드는 [05_hw_architecture_bench.py](../lab/05_hw_architecture_bench.py)에서 확인 가능합니다.
* **분석 보고서 (Analysis)**: H100의 329.7배 가속 및 Apple NE의 온디바이스 추론 효율에 대한 정량적 분석 리포트는 [05_hw_architecture_report.md](./05_hw_architecture_report.md)에 기록되어 있습니다.
* **지식 숙달 (Mastery)**: NPU의 본질과 Roofline 모델의 실행 시간 결정 원리를 검증하는 퀴즈는 [05_system_perf_expert.md](../mastery/05_system_perf_expert.md)에서 다룹니다.


### 2. 향후 확장 가능성 (Future Scope)
* 본 장에서 파이썬 모델로 분석한 NPU의 핵심 연산 블록인 **MAC(Multiply-Accumulate)** 유닛은 Unit 06에서 실제 **Verilog HDL**을 통해 하드웨어로 구현될 예정입니다. 추상적 모델링(Python)과 실제 구현(RTL) 간의 정합성을 확인하는 과정이 이어집니다.

---