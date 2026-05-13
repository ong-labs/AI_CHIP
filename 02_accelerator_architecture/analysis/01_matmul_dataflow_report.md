# 01_matmul_dataflow_report.md: Analyzing Data Reuse Strategies through Stationary Dataflows

본 보고서는 [01_matmul_loop_map_bench.py](../lab/01_matmul_loop_map_bench.py) 실습을 통해 행렬곱(Matrix Multiplication)의 6가지 루프 순서(Ordering)를 분석하고, 이를 하드웨어 가속기(NPU)의 핵심 설계 원리인 **Stationary Dataflow** 관점에서 분류 및 평가합니다.

---

## 1. Stationary Dataflow의 정의와 필요성

### 1.1 Stationary의 정의

* **한 줄 정의**: 반복문의 가장 안쪽(Inner-most loop)에서 인덱스가 변하더라도 그 값이 변하지 않는 변수, 즉 **PE(Processing Element) 내부에 고정(Stationary)되어 재사용되는 데이터**를 의미합니다.
* **핵심 원리**: 반복문의 가장 안쪽 루프에서 접근하지 않는 데이터가 하드웨어 레지스터에 고정됩니다.

### 1.2 Stationary 개념이 필요한 이유

* **데이터 이동의 비용**: 현대 반도체 아키텍처에서 데이터 이동은 연산 자체보다 훨씬 많은 에너지를 소모합니다.
* **메모리 접근 최적화**: 6가지 루프 순서에 따라 '어떤 데이터가 가장 자주 접근되는지'가 달라집니다. 가장 자주 쓰이는 데이터를 PE에 고정해 두면 외부 메모리(DRAM) 접근을 획기적으로 줄일 수 있습니다.
* **Dataflow의 핵심 아이디어**: **"데이터 이동은 비싸다. 고정 가능한 데이터는 최대한 고정한다."**

---

## 2. 6 Loop Ordering 및 3 Stationary 분류

행렬곱 연산 $C[i,j] += A[i,k] \times B[k,j]$의 세 차원 $(i, j, k)$의 순열에 따라 다음과 같이 3가지 본질적인 Dataflow로 분류됩니다.

| Order (순서) | 가장 안쪽 Loop 변수 | Inner-most에서 변하지 않는 변수 | Stationary 분류 |
| --- | --- | --- | --- |
| for i → for j → **for k** (ijk) | k | **C[i, j]** (k와 무관) | **Output Stationary** |
| for j → for i → **for k** (jik) | k | **C[i, j]** | **Output Stationary** |
| for i → for k → **for j** (ikj) | j | **A[i, k]** (j와 무관) | **Input Stationary** |
| for k → for i → **for j** (kij) | j | **A[i, k]** | **Input Stationary** |
| for j → for k → **for i** (jki) | i | **B[k, j]** (i와 무관) | **Weight Stationary** |
| for k → for j → **for i** (kji) | i | **B[k, j]** | **Weight Stationary** |

**결론**: 6가지 순서는 외부 루프의 변형일 뿐, 하드웨어 관점에서는 **본질적으로 3가지 Dataflow만 존재**합니다.

---

## 3. 세 가지 Stationary Dataflow 상세 분석

### 3.1 Output Stationary (OS)

* **코드 구조**:
```python
for i:
    for j:
        for k: # inner-most
            C[i, j] += A[i, k] * B[k, j]
```


* **핵심 아이디어**: $k$가 변하는 동안 $C[i,j]$는 같은 위치에 머무르며 하나의 출력 원소를 완성할 때까지 Partial Sum(부분합)을 PE 레지스터에 유지합니다.
* **하드웨어 설계 디테일 (보완)**: OS 방식은 부분합을 레지스터에 오래 유지해야 하므로, $INT8$ 입력 대비 정밀도 손실과 Overflow를 방지하기 위해 **32비트 이상의 Accumulator 레지스터**가 필수적입니다. 이는 데이터 재사용 효율을 높이는 대신 칩 면적(Area)이 증가하는 설계상의 주요 **트레이드오프(Trade-off)** 지점이 됩니다.
* **한 문장 요약**: 하나의 출력값($C[i,j]$)을 한 자리에서 고정된 고정밀도 레지스터를 통해 끝까지 완성하는 방식입니다.

### 3.2 Input Stationary (IS)

* **코드 구조**:
```python
for i:
    for k:
        for j: # inner-most
            C[i, j] += A[i, k] * B[k, j]
```

* **핵심 아이디어**: $j$가 변하는 동안 $A[i,k]$가 고정됩니다. 하나의 입력값을 여러 가중치(Weight)와 곱하며 입력 데이터를 최대한 재사용합니다.
* **하드웨어 설계 디테일 (보완)**: IS 방식은 하나의 입력 데이터($A[i,k]$)를 읽어와 다수의 PE에 **브로드캐스트(Broadcast)** 하여 여러 가중치와 동시에 연산할 수 있게 합니다. 이는 입력 데이터 로딩에 따르는 메모리 대역폭 부담을 줄여주며, 특히 입력 데이터의 재사용률이 높은 **컨볼루션(Convolution)** 연산 가속기 설계에서 강력한 효율을 발휘합니다.
* **한 문장 요약**: 하나의 입력값($A[i,k]$)을 한 자리에 고정하고 여러 가중치에 공유하여 데이터 읽기 비용을 최소화하는 방식입니다.

### 3.3 Weight Stationary (WS)

* **코드 구조**:
```python
for j:
    for k:
        for i: # inner-most
            C[i, j] += A[i, k] * B[k, j]
```

* **핵심 아이디어**: 루프 인덱스 $i$가 변하는 동안 **가중치($B[k, j]$)가 PE에 고정**됩니다. 하나의 가중치 값을 읽어와 여러 입력($A[i, k]$)과 곱하며 누적함으로써 가중치 데이터의 반복적인 메모리 읽기 비용을 극도로 낮춥니다.
* **하드웨어 제약 (Mixed Precision)**: 부분합을 누적하는 동안 **Overflow**를 방지하기 위해, 입력 데이터($INT8$)보다 훨씬 큰 비트 수의 **32비트 Accumulator 레지스터**가 필수적입니다. 이는 데이터 재사용 효율과 칩 면적(Area) 사이의 중요한 설계 트레이드오프 지점이 됩니다.
* **한 문장 요약**: 하나의 출력값을 한 자리에서 **32비트 정밀도**로 끝까지 완성하는 방식입니다.

---

## 4. 데이터 흐름의 비유 및 에너지 효율 분석

### 4.1 공장 라인 비유

| Dataflow | 비유 | 고정되는 것 (Stationary) | 이동하는 것 |
| --- | --- | --- | --- |
| **OS** | 조립대에서 제품을 완성 | 작업 대상 ($C[i,j]$) | 부품 ($A, B$) |
| **IS** | 재료를 들고 여러 도구를 사용 | 재료 ($A[i,k]$) | 도구 ($B$) |
| **WS** | 도구를 고정하고 재료를 공급 | 도구 ($B[k,j]$) | 재료 ($A$) |

### 4.2 하드웨어 레벨의 에너지 소모 비교

PE 레지스터에 데이터를 고정하는 것은 외부 메모리 접근 에너지를 획기적으로 줄여줍니다.

| 데이터 위치 | 1 Byte 접근 에너지 | 비유 |
| --- | --- | --- |
| **DRAM (Off-chip)** | **~100 pJ** | 옆 건물에서 가져오기 |
| **SRAM (On-chip)** | **~5 pJ** | 같은 층에서 가져오기 |
| **PE Register** | **~1 pJ** | **손에 들고 있기** |

**결론**: Stationary 데이터는 손에 들고 작업하는 것과 같아 매번 다시 가져올 필요가 없으므로 압도적으로 효율적입니다.

---

## 5. 아키텍처 결정: 워크로드와 TPU의 선택

### 5.1 Stationary별 적합 워크로드

| Stationary | 주로 줄어드는 비용 | 적합한 워크로드 |
| --- | --- | --- |
| **Weight Stationary** | Weight Read 감소 | **AI 추론, 큰 Batch 사이즈** |
| **Output Stationary** | Partial Sum Read/Write 감소 | Output accumulation(누적) 중심 |
| **Input Stationary** | Input Read 감소 | Input 재사용률이 높은 경우 |

### 5.2 TPU(Tensor Processing Unit)가 WS를 선택한 이유

Google의 TPU는 **Weight Stationary**를 채택했습니다.

1. **추론 특화**: 학습이 끝난 가중치(Weight)는 추론 동안 변하지 않고 고정됩니다.
2. **높은 재사용성**: 동일한 모델(Weight)을 수많은 입력 데이터에 반복 적용하므로 가중치 재사용률이 극도로 높습니다.
3. **DRAM 접근 최소화**: 가중치를 한 번 PE에 올리면 가능한 오래 사용함으로써 에너지가 비싼 DRAM 접근을 최소화합니다.

---

### 6. 요약

  같은 행렬곱 연산이라도 '무엇을 고정하느냐'에 따라 하드웨어 내부의 데이터 흐름과 에너지 소모는 완전히 달라집니다. [01_matmul_loop_map_bench.py](../lab/01_matmul_loop_map_bench.py) 실습을 통해 확인했듯이, 루프 순서는 단순한 코드 스타일이 아닌 **하드웨어 아키텍처의 정체성**을 결정하는 핵심 설계 요소입니다.
