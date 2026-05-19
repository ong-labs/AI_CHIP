# 03_dataflow_cost_report.md: Comparison of WS / OS / IS Dataflows

본 보고서는 [03_memory_access_bench.py](../lab/03_memory_access_bench.py)를 기반으로 작성되었습니다. AI 반도체 설계에서 '같은 결과(C = A @ B)를 내더라도 데이터를 어떻게 움직여야 가장 적은 비용으로 계산할 수 있는가?'라는 핵심 질문에 답하기 위해 데이터 재사용 방식에 따른 DRAM 접근량과 내부 데이터 이동량을 정량적으로 분석합니다.

---

## 1. Eyeriss 분류와 메모리 비용 모델

### 1.1 Dataflow의 분류

MIT의 Eyeriss 논문은 대표적인 데이터 흐름(Dataflow)을 다음과 같이 네 가지로 분류하였습니다.

* **Weight Stationary (WS)**: 가중치 고정
* **Output Stationary (OS)**: 출력(부분합) 고정
* **Input Stationary (IS)**: 입력 데이터 고정
* **Row Stationary (RS)**: 행 데이터 고정

### 1.2 메모리 계층별 에너지 비용

데이터를 어디에 오래 머물게(Stationary) 할 것인가가 에너지 효율의 핵심입니다.

| 메모리 계층 | 에너지/Byte (대략) | 비고 |
| --- | --- | --- |
| **DRAM** | ~100 pJ | Register 접근 대비 수백 배 비용 발생 |
| **SRAM** | ~5 pJ | 온칩 메모리 수준 |
| **PE Register** | ~1 pJ | 연산기 바로 옆 최저 비용 |

**핵심 통찰**: DRAM 한 번 접근하는 비용은 Register를 수십~수백 번 접근하는 비용과 맞먹습니다. 따라서 데이터 이동을 최소화하는 설계가 필수적입니다.

---

## 2. 메모리 접근 분석 모델 (`simulate`)

본 코드는 같은 행렬 곱셈($C = A \times B$)을 세 가지 데이터플로우로 시뮬레이션하여 비용을 산출합니다.

* **연산 전제**: $A(M \times K) \times B(K \times N) = C(M \times N)$
* **검증 기준**: 모든 Dataflow에서 `np.allclose(C, A @ B)` 결과는 **True**이나, 메모리 접근량은 서로 다릅니다.
* **측정 핵심 지표**:
  * **cycles**: 예상 실행 시간
  * **dram_read_bytes**: DRAM에서 읽은 총 데이터 양
  * **dram_write_bytes**: DRAM에 기록한 총 데이터 양
  * **pe_moves**: PE 간 내부 데이터 이동량

---

## 3. 세 가지 데이터플로우 상세 분석

### 3.1 Weight Stationary (WS)

* **메커니즘**: 가중치 $B$를 PE 내부에 고정(Stationary)합니다.
* **PE 내부 동작**: `weight` = 고정, `input` = 계속 흐름, `psum` = 누산 후 저장
* **적합한 사례**: Fully Connected Layer, 추론(Inference), 동일 가중치를 반복 사용하는 경우
* **장점**: Weight DRAM Read를 최소화합니다.

### 3.2 Output Stationary (OS)

* **메커니즘**: 출력 $C$의 부분합(Partial Sum)을 PE 내부에 고정합니다.
* **PE 내부 동작**: `output partial sum` = 고정, `A, B` = 계속 공급
* **적합한 사례**: 일반적인 GEMM 연산, TPU의 대표적인 데이터플로우
* **장점**: 부분합을 내부에서 누적하여 Output DRAM Write를 최소화합니다.

> 대규모 행렬곱에서 DRAM 트래픽은 WS/IS보다 높을 수 있으나, 데이터 버스(Data Bus)의 비트 폭이 넓은 고성능 가속기 설계 시 제어 로직을 단순화할 수 있는 강력한 이점이 있습니다.

### 3.3 Input Stationary (IS)

* **메커니즘**: 입력 $A$를 PE 내부에 고정합니다.
* **PE 내부 동작**: `input` = 고정, `weights` = 계속 흐름
* **적합한 사례**: 동일 입력으로 많은 출력을 계산하는 경우, GEMV, Transformer의 특정 연산
* **장점**: Input DRAM Read를 최소화합니다.

---

## 4. 정량적 시뮬레이션 결과 (Quantitative Simulation Results)

본 섹션은 [03_memory_access_bench.py](../lab/03_memory_access_bench.py)를 사용하여 $4 \times 4$ PE Array 환경에서 5가지 주요 워크로드를 시뮬레이션한 결과입니다.

### 4.1 소규모 및 일반 연산 (Tiny & Mid)

배열 크기에 딱 맞거나 균형 잡힌 크기의 연산에서는 가중치 재사용성이 높은 WS가 미세하게 유리한 지표를 보입니다.

| 워크로드 | Dataflow | Cycles | DRAM Read (MB) | PE Moves | 비고 |
| --- | --- | --- | --- | --- | --- |
| **Tiny** | **WS** | **88** | **0.001** | **512** | **Lowest DRAM Traffic** |
| (8x8x8) | OS | 64 | 0.001 | 256 | 최단 사이클 |
|  | IS | 88 | 0.001 | 512 |  |
| **Mid** | **WS** | **45,056** | **0.279** | **262,144** | **Lowest DRAM Traffic** |
| (64x64x64) | OS | 32,768 | 0.524 | 131,072 |  |
|  | IS | 45,056 | 0.279 | 262,144 |  |

### 4.2 Batched FC Layer (M=256, K=4096, N=64)

가중치($K \times N$) 대비 배치 사이즈($M$)가 큰 워크로드입니다.

* **최적 Dataflow**: **Weight Stationary (WS)**
* **DRAM Traffic**: WS(68.1 MB) vs OS(134.2 MB) vs IS(71.3 MB)
* **분석**: 가중치 행렬이 크고 반복적으로 사용되므로, 이를 PE에 고정하는 WS 방식이 OS 대비 DRAM 접근량을 약 **50% 절감**합니다.

### 4.3 Single-batch GEMV (M=1, K=4096, N=4096)

입력 벡터가 하나뿐인 추론 상황으로, AI 가속기 설계에서 가장 까다로운 워크로드 중 하나입니다.

* **최적 Dataflow**: **Input Stationary (IS)**
* **DRAM Read**: **67.1 MB (IS)** vs 134.2 MB (WS/OS)
* **분석**: 입력 데이터($M=1$)를 한 번만 읽어 PE에 고정한 뒤 모든 가중치와 연산하게 함으로써, DRAM 읽기 비용을 타 방식 대비 **절반 수준**으로 떨어뜨리는 압도적 효율을 보입니다.

### 4.4 Large Balanced MatMul (4096x4096x4096)

초대형 정사각 행렬 연산입니다.

| Dataflow | DRAM Read (MB) | PE Moves | 비고 |
| --- | --- | --- | --- |
| **WS** | **68,786.5** | **68,719,476,736** | **Lowest DRAM Traffic** |
| OS | 137,438.9 | 34,359,738,368 |  |
| **IS** | **68,786.5** | **68,719,476,736** | WS와 대등한 효율 |

* **분석**: 대규모 연산에서는 가중치와 입력의 재사용률이 모두 극대화되므로 WS와 IS가 유사한 효율을 보이나, OS는 중간 부분합 배출 비용으로 인해 약 **2배 더 많은 DRAM 트래픽**이 발생합니다.

---

## 5. 최종 메시지 및 통찰 (Architecture Conclusion)

시뮬레이션 결과는 "연산(Compute)은 저렴하지만, 데이터 이동(Data Movement)은 비싸다"는 하드웨어 설계의 대전제를 수치로 증명합니다.

1. **데이터플로우의 상대성**: 모든 상황에 완벽한 데이터플로우는 없습니다. 워크로드의 형태에 따라 최적의 아키텍처는 변합니다.
2. **에너지 효율의 핵심**: DRAM 접근(100 pJ)을 최소화하기 위해 데이터를 PE Register(1 pJ)에 얼마나 오래 머물게 하느냐가 전체 NPU의 전성비를 결정합니다.
3. **설계 전략**: 추론 중심 NPU라면 **IS/WS**의 유연한 조합을, 범용 GEMM 가속기라면 **OS/WS**의 밸런스를 고려해야 합니다.

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 데이터플로우별 비용 시뮬레이션의 전체 소스 코드는 [03_memory_access_bench.py](../lab/03_memory_access_bench.py)에서 확인할 수 있습니다.
* **연계 학습**: 이 분석은 [02_accelerator_mastery.md]에서 다룬 시스톨릭 어레이의 물리적 구조가 실제 메모리 트래픽과 에너지 소모에 미치는 영향을 정량적으로 확장한 것입니다.

### 2. 가속기 설계의 정수 (Hardware Insight)
* 데이터플로우의 선택은 고정된 하드웨어 자원 내에서 '어떤 데이터를 머물게 하고 어떤 데이터를 흐르게 할 것인가'를 결정하는 전략적 선택입니다. 이 보고서에서 다룬 $M=1$ 상황의 IS 방식 효율성 수치는 향후 온디바이스 AI 가속기 설계에서 SRAM 계층 구조와 제어 로직(FSM)을 최적화하는 데 있어 가장 중요한 설계 근거가 될 것입니다.
