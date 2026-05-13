# 04_roofline_report.md: Understanding MatMul Performance Limits and Bottlenecks through the Roofline Model

본 보고서는 [04_roofline_bench.py](../lab/04_roofline_bench.py)로 측정한 CPU 실측치와 GPU 이론 예측치를 비교하여 성능 병목을 분석합니다. 실습 데이터의 Reuse Factor와 활용률을 바탕으로 이론과 현실의 간극을 분석하고, GPU 가속의 수치적 근거를 기록합니다.

> **💡 이론적 배경 확인**: 본 실험에서 사용한 **Arithmetic Intensity(AI)** 의 정의와 **임계 AI($AI_{critical}$)** 를 통한 병목 판정 원리에 대한 이론적 설명은 [04_roofline_model.md](./04_roofline_model.md) 문서에서 상세히 다루고 있습니다.


**추가 분석 목표:**
* CPU 실측 성능 평가
* GPU 이론적 성능 예측
* Arithmetic Intensity (AI, 산술 연산 밀도) 분석
* Compute-bound와 Memory-bound의 판별

---

## 1. 전체 구조

실습 코드는 크게 두 파트로 구성되어 있습니다.

| Part | 목적 |
| :--- | :--- |
| **Part 1** | CPU 실측 결과와 Roofline 이론 예측치의 비교 검증 |
| **Part 2** | 동일 알고리즘에 대한 GPU 성능 이론 예측 및 비교 |

---

## 2. Roofline Model 핵심 개념

Roofline 모델은 시스템의 실제 성능이 다음 두 가지 제약 중 **더 느린 쪽(시간이 더 걸리는 쪽)** 에 의해 결정된다고 정의합니다.

1. **연산 능력 (Compute)**
2. **메모리 전송 능력 (Memory Bandwidth)**

즉, 전체 실행 시간은 다음과 같이 정의됩니다.
> **실행 시간 = $\max$(Compute Time, Memory Time)**

---

## 3. 핵심 데이터 구조 및 함수 분석

### 3.1 RooflineResult 데이터 클래스
Roofline 계산 결과를 저장하기 위한 구조체입니다.

```python
@dataclass
class RooflineResult:
    time_s: float
    gflops: float
    ai: float
    bound: str
```

| 필드 | 의미 |
| --- | --- |
| **time_s** | 예상 실행 시간 |
| **gflops** | 예상 GFLOPS |
| **ai** | Arithmetic Intensity (산술 연산 밀도) |
| **bound** | 병목 원인 (compute 또는 memory) |

### 3.2 `roofline_estimate()`: 핵심 함수 상세

Roofline 모델의 이론적 한계를 도출하는 핵심 함수로, 다음의 단계별 수식을 적용합니다.

#### A. FLOPS 계산

* **수식**: `flops = 2 * n * m * k`
* **배경**: 행렬곱 $C_{n \times m} = A_{n \times k} \times B_{k \times m}$ 연산 시, 원소당 multiply 1회와 add 1회가 발생하여 **총 2 FLOPs**가 수행됩니다.
* **예시**: $N=4096$인 경우, $4096^3 \times 2 \approx 137\text{ GFLOPs}$가 발생합니다.

#### B. 메모리 사용량 계산

* **Naive Bytes**: `bytes_naive = (n*k + k*m + n*m) * dtype_bytes`
* **배경**: 행렬 A 읽기, 행렬 B 읽기, 행렬 C 쓰기에 필요한 총 바이트 수를 의미합니다.

#### C. Reuse Factor (재사용 계수)

* **수식**: `bytes_actual = bytes_naive / reuse_factor`
* **의미**: 하드웨어의 '캐시 재사용 효과'를 근사하는 매우 중요한 지표입니다.
* **Naive**: 매 연산마다 DRAM에 직접 접근하는 최악의 상황.
* **실제(Actual)**: 캐시 계층을 통한 Cache Reuse 발생.

> **💡 왜 GPU의 `reuse_factor`가 매우 큰가?**
> "RTX 4090"의 경우 `reuse: 64`, "H100"의 경우 `reuse: 128`에 달합니다. GPU는 아키텍처 레벨에서 **Shared Memory, Tiling, Tensor Core Blocking**을 강하게 지원하여 데이터 재사용성을 극대화하기 때문입니다.

#### D. Compute Time (연산 소요 시간)

* **수식**: `t_compute = flops / (peak_gflops * 1e9)`
* **공식**: $t_{compute}=\frac{FLOPs}{Peak\ FLOPS}$
* **예시**: 100 GFLOP 작업을 10 TFLOPS 성능의 GPU에서 처리하는 데 걸리는 시간.

#### E. Memory Time (메모리 소요 시간)

* **수식**: `t_memory = bytes_actual / (peak_bw_gbps * 1e9)`
* **공식**: $t_{memory}=\frac{Bytes}{Bandwidth}$
* **의미**: 메모리(DRAM)에서 연산기로 데이터를 가져오는 데 걸리는 시간입니다.

#### F. 병목 판정 (Bottleneck Determination)

```python
if t_compute >= t_memory:
```

* **의미**: 연산 시간이 더 오래 걸린다면 연산기가 병목이 되는 **Compute Bound** 상태입니다.
* **반대면**: 데이터 전송이 지연되는 **Memory Bound** 상태입니다.

#### 🎯 핵심 철학 요약

Roofline 모델의 본질은 다음 공식으로 귀결됩니다.

$$Performance\leq\min(Peak\ Compute,\ AI\times Bandwidth)$$

---

## 4. 하드웨어 스펙 및 실측 분석

### 4.1 SPECS_FP32 (하드웨어 스펙 테이블)

다양한 하드웨어의 연산 제원을 정의합니다.

```python
SPECS_FP32 = {
    "RTX 4090": {
        "peak_gflops": 82_000,
        "peak_bw": 1008,
        "reuse": 64
    }
}
```

| 항목 | 의미 |
| --- | --- |
| **peak_gflops** | FP32 최대 연산량 |
| **peak_bw** | 메모리 대역폭 (Bandwidth) |
| **reuse** | Cache 및 Shared Memory 효과 |

### 4.2 `measured_cpu_matmul()` (실제 CPU 측정)

* **동작**: `_ = A @ B` 코드를 통해 CPU의 실제 연산 성능을 측정합니다.
* **왜 NumPy가 빠른가?**: `A @ B` 연산은 단순한 Python 루프가 아닙니다. 내부적으로 **BLAS, Accelerate, OpenBLAS, MKL**과 같은 고도로 최적화된 커널(highly optimized kernel)을 호출하며, 이 과정에서 **SIMD, Cache Blocking, AMX, Vectorization** 기술을 모두 사용하기 때문입니다.

---

## 5. 실행 파트별 분석 (Actual Execution Data)

본 섹션에서는 `04_roofline_bench.py`를 실행하여 도출된 실측 데이터를 바탕으로 모델의 정확도를 검증합니다.

### 5.1 Part 1: CPU 실측 기반 모델 검증
모델이 예측한 시간과 실제 CPU(Apple M-class + AMX)에서 측정한 시간을 비교합니다.

* **실측 데이터 기록**:
    * **N=2048**: Predicted 5.73ms vs Measured **32.68ms** (Ratio: **0.18x**)
    * **N=4096**: Predicted 45.81ms vs Measured **260.68ms** (Ratio: **0.18x**)
* **데이터 해석 (Insight)**:
    * 예측 대비 실측 시간이 약 5.5배($1/0.18$) 더 느리게 측정되었습니다. 이는 모델이 AMX의 이론적 최대 성능(3000 GFLOPS)을 가정했으나, 실제 NumPy 연산 시에는 라이브러리 오버헤드나 하드웨어 활용률 저하로 인해 약 **527 GFLOPS** 수준의 실효 성능만 기록되었음을 의미합니다.
    * 하지만 **Ratio가 0.18x로 일정**하다는 점은, 모델의 수식 자체는 하드웨어의 스케일링을 정확하게 반영하고 있음을 시사합니다.

### 5.2 Part 2: GPU 성능 이론 예측
동일한 로직에 하드웨어 파라미터만 변경하여 GPU의 잠재 성능을 예측한 결과입니다.

| Hardware | N=4096 ms (Pred) | Bound Type | Speedup vs CPU |
| :--- | :---: | :---: | :---: |
| **CPU (M-class + AMX)** | 45.81 ms | compute | 1.0x |
| **RTX 4090** | **1.67 ms** | compute | **27.3x** |
| **H100 SXM** | **2.05 ms** | compute | **22.3x** |
| **Apple M2 GPU** | 38.17 ms | compute | 1.2x |

* **데이터 해석 (Insight)**:
    * **Compute-bound의 지배**: 모든 고성능 장치에서 MatMul은 Compute-bound로 나타납니다. 이는 높은 `reuse_factor` 덕분에 메모리 대역폭이 병목이 되지 않고 연산기 성능이 그대로 결과에 반영됨을 뜻합니다.
    * **RTX 4090 vs H100**: 재미있게도 FP32 연산에서는 4090(82 TFLOPS)이 H100(67 TFLOPS)보다 빠르게 예측되었습니다. 이는 H100이 AI 학습(FP8/FP16)에 특화된 반면, 순수 FP32 연산력은 4090이 매우 강력하기 때문입니다.

---

## 6. 교육적으로 가장 중요한 4대 포인트

본 실습 코드가 시사하는 진짜 핵심은 다음과 같습니다.

### 핵심 1. 성능은 단순 Clock Speed가 아니다.

성능의 본질은 클럭 속도가 아니라 Compute 연산력과 Memory 대역폭 간의 균형(Compute vs Memory)에 있습니다.

### 핵심 2. GPU가 빠른 이유는 단순 Core 수 때문이 아니다.

코어 개수 외에도 다음과 같은 압도적인 스펙이 GPU의 속도를 결정합니다.

* 매우 큰 **Bandwidth**
* **Reuse**의 극대화 아키텍처
* 거대한 수준의 **병렬성(Parallelism)**

### 핵심 3. Arithmetic Intensity (AI)와 시스템 레벨 병목

* **정의**: $AI = \frac{FLOPs}{Bytes}$ (데이터 1바이트당 수행되는 연산량)
* **결론**: AI가 높을수록 **Compute-bound** 영역에 진입하여 GPU 효율이 극대화됩니다. 행렬곱은 대표적인 고-AI 연산입니다.
* **시스템 병목의 확장 (H2D)**: Roofline 모델은 칩 내부 연산에 집중하지만, 실제 환경에서는 PCIe를 통한 Host-to-Device (H2D) 전송 시간($T_{transfer}$)이 순수 연산 시간($T_{compute} \approx 1.67ms$)보다 수십 배 길어질 수 있습니다. 따라서 진정한 가속은 연산 최적화와 데이터 전송 최소화를 동시에 고려해야 합니다.


### 핵심 4. 행렬곱이 AI/HPC 생태계에서 중요한 이유

행렬곱 연산은 다음과 같은 최적화 친화적 특성을 가집니다.

* 데이터 **Reuse**가 높음
* **Blocking(Tiling)** 최적화가 가능
* **SIMD** 명령어 활용에 매우 친화적
* **GPU** 하드웨어 구조에 매우 친화적

위와 같은 이유로 행렬곱은 현대 **AI, 딥러닝, HPC(고성능 컴퓨팅)** 분야에서 시스템을 구동하는 가장 핵심적인 Primitive(기본 연산)로 채택되어 사용되고 있습니다.

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 보고서의 데이터 도출에 사용된 벤치마크 및 예측 시뮬레이션 코드는 [04_roofline_bench.py](../lab/04_roofline_bench.py)에서 확인 가능합니다.
 * **이론적 배경 (Analysis)**: Roofline 모델의 핵심 수식($T_{actual} \approx \max(T_{compute}, T_{memory})$) 및 기기별 스펙 분석은 [04_roofline_model.md](./04_roofline_model.md)에 기술되어 있습니다.
 

### 2. 데이터 신뢰성 안내
* 본 보고서의 **Ratio (0.18x)** 결과는 특정 라이브러리(NumPy/Accelerate) 환경에서의 활용률을 나타냅니다. 실제 성능 최적화 단계에서는 컴파일러 옵션 및 저수준 가속 라이브러리(MKL, OneDNN) 활용에 따라 이 수치가 변동될 수 있음을 유의하시기 바랍니다.
