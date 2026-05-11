# 04_roofline_model.md: Performance Modeling and Bound Analysis

본 문서는 [04_roofline_bench.py](../lab/04_roofline_bench.py)의 시뮬레이션 엔진이 되는 Roofline 모델의 이론적 기반을 다룹니다. 단순 스펙 비교를 넘어 산술 연산 밀도(AI)를 통해 시스템 병목을 정량화하며, 동일한 수식으로 CPU와 GPU의 성능을 통합 예측하는 모델링 역량을 학습합니다.

> **🚀 실측 데이터 검증**: 본 문서에서 정의한 Roofline 모델 수식과 $AI_{critical}$ 이론이 실제 Apple M-class AMX 및 RTX 4090 환경에서 어떻게 성능 병목을 예측하는지는 04_roofline_report.md 실측 보고서에서 확인하실 수 있습니다.

---

## 1. Roofline 모델 개요

### 학습 목표

* **Bottleneck 판별**: 워크로드가 Compute-bound인지 Memory-bound인지 판별하는 도구로 활용합니다.
* **정량적 예측**: 파라미터화된 성능 모델을 코딩하여 CPU와 GPU의 스펙을 동일한 수식에 대입하고 성능을 예측합니다.
* **아키텍처 이해**: "GPU는 코어(Lane)가 많다"라는 정성적 진술을 구체적인 수치로 정량화합니다.

---

## 2. Roofline 이론 (Roofline Theory)

### 2.1 핵심 공식

실행 시간은 **연산 한계**와 **메모리 한계** 중 더 느린 쪽(시간이 더 오래 걸리는 쪽)에 의해 결정됩니다.

$$T_{compute} = \frac{\text{Total FLOPs}}{\text{Peak GFLOPS/sec}}$$

$$T_{memory} = \frac{\text{Bytes Moved}}{\text{Peak Bandwidth/sec}}$$

$$T_{actual} \approx \max(T_{compute}, T_{memory})$$

### 2.2 산술 연산 밀도 (Arithmetic Intensity, AI)

연산의 성격을 규정하는 지표로, 메모리에서 1바이트를 가져올 때 수행하는 연산의 횟수를 의미합니다.

$$AI = \frac{\text{FLOPs}}{\text{Bytes Moved}} \quad \text{(Unit: FLOPs/byte)}$$

| 구분 | AI가 낮을 때 | AI가 높을 때 |
| --- | --- | --- |
| **상태** | **Memory-bound** | **Compute-bound** |
| **병목 원인** | 메모리 전송 속도가 연산을 못 따라감 | 연산기 처리 능력이 전송을 못 따라감 |
| **개선 방향** | 대역폭(BW)을 늘려야 빨라짐 | 연산 능력(Peak)을 늘려야 빨라짐 |

### 2.3 임계 AI (Critical AI)

칩의 하드웨어적 균형점을 의미하며, 이 값을 기준으로 워크로드의 성격이 나뉩니다.

$$AI_{critical} = \frac{\text{Peak GFLOPS}}{\text{Peak BW (GB/s)}}$$

* **워크로드 AI < 임계 AI**: Memory-bound
* **워크로드 AI > 임계 AI**: Compute-bound
* 칩마다 하드웨어 설계 명세가 다르므로 **임계 AI는 칩마다 상이**합니다.

---

## 3. MatMul의 AI 분석 (N × N × N, float32)

행렬 곱셈은 전형적인 **Compute-bound** 워크로드입니다. 데이터 재사용성이 높기 때문입니다.

| 항목 | 계산식 | N=4096 기준 수치 |
| --- | --- | --- |
| **FLOPs** | $2N^3$ | $1.37 \times 10^{11}$ |
| **Bytes (naive)** | $12N^2$ | $2.0 \times 10^8$ |
| **AI** | $N/6$ | **~683 FLOPs/byte** |

* **결론**: $N=4096$ MatMul의 AI(683)는 대부분 기기의 임계 AI(10~100)를 훨씬 상회하므로, 대부분의 컴퓨팅 환경에서 **Compute-bound**로 분류됩니다.

---

## 4. 기기별 하드웨어 스펙 및 임계 AI 예시

현대적인 고성능 프로세서들의 이론적 균형점입니다.

| 기기명 | Peak GFLOPS (FP32) | BW (GB/s) | **임계 AI** |
| --- | --- | --- | --- |
| **Intel i9-13900K** | ~1500 | 90 | **~17** |
| **Apple M-class (CPU+AMX)** | ~3000 (실측) | 200 | **~15** |
| **NVIDIA RTX 4090** | ~82,000 | 1008 | **~81** |
| **NVIDIA H100 SXM** | ~67,000 | 3350 | **~20** |

* *참고: 위 수치는 명목 스펙이며, 실제 구현 시에는 약 60~80% 수준에 도달하는 것이 일반적입니다.*

---

## 5. 모델 검증 및 응용

### 5.1 CPU 모델 측정값 검증

* **의도**: 작성한 모델을 기존 측정값(Unit 01/03의 NumPy MatMul)과 비교하여 신뢰도를 확보합니다.
* **기준**: 모델 예측치가 측정값의 **0.5x ~ 2x 범위** 내에 들어오면 유효한 모델로 판단합니다.
* **주의**: Apple Silicon의 경우 `py-cpuinfo`의 단순 공식을 쓰면 AMX 가속기가 반영되지 않아 실측 성능과 5배 이상 차이 날 수 있으므로, 실측 Peak 성능을 사용해야 합니다.

>* **실측 데이터 기록**:
>    * **N=2048**: Predicted 5.73ms vs Measured **32.68ms** (Ratio: **0.18x**)
>    * **N=4096**: Predicted 45.81ms vs Measured **260.68ms** (Ratio: **0.18x**)
>
>* **데이터 해석 (Insight: 하드웨어 시스템의 제약)**:
>    * **Power & Thermal Throttling**: 예측 대비 약 5.5배 느린 실측치의 주요 원인 중 하나는 랩탑 환경의 물리적 제약입니다. 모든 코어를 가동하는 대규모 행렬 연산 시, 시스템은 전력 소모를 줄이고 발열을 제어하기 위해 **Power Limit**을 걸거나 클럭 속도를 강제로 낮추는 **Thermal Throttling**을 수행합니다.

### 5.2 타일링(Tiling)과 재사용 계수 (Reuse Factor)

* **함정**: 단순 계산(`reuse_factor=1.0`)은 메모리 접근을 지나치게 과대평가합니다.
* **현실**: 실제 BLAS 라이브러리는 타일링 기법을 통해 데이터를 수십~수백 회 재사용합니다. 이것이 MatMul이 실제 환경에서 Memory-bound가 아닌 Compute-bound로 동작하는 결정적 이유입니다. 모델에 `reuse_factor`를 도입하면 실측치와 더 높은 정합성을 보입니다.

### 5.3 정밀도(Precision)에 따른 AI 변화와 병목 지점의 이동

AI 반도체 아키텍처 설계 관점에서 데이터의 정밀도는 성능과 병목 지점을 결정하는 핵심 변수입니다.

* **연산 성능의 비약적 상승**: $float32$에서 $FP16, BF16, INT8$로 정밀도를 낮출수록, 하드웨어는 동일한 시간에 더 많은 데이터를 처리할 수 있어 $Peak\ GFLOPS$가 보통 2배에서 4배까지 비약적으로 상승합니다.
* **대역폭 소모 감소**: 데이터당 비트 수가 줄어들어 $Bandwidth$ 소모량(바이트 수)은 감소합니다.
* **결과 (Bottleneck Shift)**: 결과적으로 $AI_{critical}$($Peak\ GFLOPS / BW$) 수치가 급격히 높아집니다. 이는 과거에 **Compute-bound**였던 워크로드가 저정밀도 연산 환경에서는 **Memory-bound**로 이동할 수 있음을 시사하며, AI 반도체 설계 시 메모리 대역폭 확보가 왜 중요한지를 증명하는 지표가 됩니다.

### 5.4 성능 모델링의 정수: Roofline Graph 시각화

성능 모델링의 핵심은 복잡한 하드웨어 수치를 직관적인 그래프로 변환하는 데 있습니다.

* **X축 (Arithmetic Intensity)**: 워크로드의 연산 밀도를 로그 스케일로 표시합니다.
* **Y축 (Performance, GFLOPS)**: 도달 가능한 성능을 표시합니다.
* **해석**: 대각선의 'Roof'는 메모리 한계를, 수평선의 'Ceiling'은 연산 한계를 나타냅니다. 실측 데이터가 이 그래프의 어느 지점에 위치하는지를 통해 현재 시스템의 최적화 수준을 정량적으로 파악할 수 있습니다.

---

## 6. 분석 및 회고 (Analysis & Reflection)

### 6.1 N 스윕 (N Sweep)

데이터 크기($N$) 변화에 따른 병목 지점의 전이 현상을 관찰합니다.

* **작은 N**: 전체 데이터량 대비 메모리 이동 비중이 높아 **Memory-bound** 영역에 인접합니다.
* **큰 N**: 연산량이 기하급수적으로 늘어나며 **Compute-bound** 확정 영역으로 진입합니다.

### 6.2 재사용 계수 스윕 (Reuse Factor Sweep)

소프트웨어 최적화 수준에 따른 변화를 관찰합니다.

* **낮은 Reuse**: 알고리즘이 비효율적일 경우 강력한 연산기를 두고도 메모리 속도에 갇히는 Memory-bound가 됩니다.
* **높은 Reuse**: 고도로 최적화된 BLAS는 타일링을 통해 Reuse를 수십 배 끌어올려 성능을 Compute-bound 영역으로 견인합니다.

---

## 7. 막힘 포인트 및 해결 가이드 (Troubleshooting)

| 증상 | 원인 | 해결책 |
| --- | --- | --- |
| **GPU 예측이 CPU보다 느림** | TFLOPS 단위를 GFLOPS로 오입력 | 단위 검증 (RTX 4090 = 82,000 GFLOPS) |
| **모든 케이스가 Memory-bound** | `reuse_factor` 누락 또는 과소 설정 | 실제 BLAS는 수십 회 이상의 reuse를 수행함 |
| **CPU 모델이 100x 빠르게 예측** | 활용률 100%를 가정한 이론적 수치 사용 | 실측 활용률(0.5~0.7)을 곱하여 보정 |
| **AI 단위 혼동** | FLOPs/byte와 FLOPs/element 혼용 | **byte 기준**으로 통일, 식에 `dtype_bytes` 포함 |

---

## 🎯 핵심 메시지 (Core Insight)

1. **일반화 가능성**: 하나의 식이 서로 다른 하드웨어 아키텍처(CPU, GPU, NPU)를 모두 설명할 수 있습니다.
2. **예측력**: Peak GFLOPS와 Bandwidth라는 두 축만 알면 어떤 칩의 어떤 워크로드든 병목 지점과 성능 한계치를 예측할 수 있습니다.
3. **본질의 동일성**: CPU와 GPU는 근본적으로 다른 기계가 아닙니다. **연산 능력과 대역폭이라는 파라미터 값이 다를 뿐**, 동일한 성능 모델 하에서 움직이는 연산 장치입니다.

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 문서의 파라미터화된 성능 모델을 실제로 구현하고 CPU/GPU 성능을 시뮬레이션하는 코드는 [04_roofline_bench.py](../lab/04_roofline_bench.py)에서 확인 가능합니다.
* **분석 보고서 (Analysis)**: 이론적 예측치와 실측 데이터 사이의 오차(Ratio 0.18x)에 대한 심층 분석 리포트는 [04_roofline_report.md](./04_roofline_report.md)에 기록되어 있습니다.
* **지식 숙달 (Mastery)**: Roofline 모델의 핵심인 AI와 Bound 판별 개념을 검증하는 퀴즈는 [04_performance_modeling.md](../mastery/04_performance_modeling.md)에서 다룹니다.

### 2. 향후 확장 가능성 (Future Scope)
* 본 장에서 다룬 **Roofline 분석**은 시스템의 절대적 성능 한계를 파악하는 기준이 됩니다. 다음 유닛에서는 이 분석을 바탕으로 **Memory-bound** 워크로드를 **Compute-bound**로 전환하기 위한 **커널 퓨전(Kernel Fusion)** 및 **레지스터 블로킹(Register Blocking)** 기법을 학습할 예정입니다.
