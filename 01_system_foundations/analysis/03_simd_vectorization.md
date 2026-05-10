# 03_simd_vectorization.md: Harnessing Parallelism for Computational Peak

본 문서는 [03_simd_bench.py](../lab/03_simd_bench.py)를 통해 현대 CPU의 핵심 병렬 연산 기술인 **SIMD(Single Instruction Multiple Data)** 의 원리를 이해하고, 하드웨어의 이론적 최대 성능(Peak GFLOPS)과 실측 성능 사이의 간극을 분석하는 데 중점을 둡니다.

> **🚀 실측 데이터 검증**: 본 문서에서 다루는 $SIMD$ 레인 폭과 $FMA$ 가중치 이론이 실제 $13th\ Gen\ Intel\ Core\ i9$ 환경에서 어떻게 수치로 증명되었는지는 03_simd_execution_report.md 실측 보고서에서 확인하실 수 있습니다.

---

## 1. SIMD 이론 (SIMD Theory)

### 1.1 SIMD 핵심 개념
SIMD는 하나의 명령어로 여러 개의 데이터를 동시에 처리하는 병렬 처리 방식입니다. 기존의 스칼라(Scalar) 방식이 한 번에 하나의 연산만 수행했다면, SIMD는 레지스터를 여러 개의 'Lane'으로 나누어 벡터 연산을 수행합니다.

| 방식 | 연산 예시 | 1 Cycle 당 처리량 |
| :--- | :--- | :--- |
| **스칼라(Scalar) add** | `c = a + b` | 1 float |
| **SIMD add** | `[c0..c7] = [a0..a7] + [b0..b7]` | **8 float** (AVX2 기준) |

### 1.2 Lane 폭 (Architecture 별)
CPU 아키텍처에 따라 지원하는 명령어 집합(ISA)과 레지스터 폭이 다르며, 이는 한 번에 처리할 수 있는 데이터의 개수를 결정합니다. 

> **ℹ️ 정밀도(Precision)의 중요성**: 아래 표는 단정밀도(`float32` - 4 bytes) 기준입니다. 과학 연산에서 자주 쓰이는 배정밀도(`float64` - 8 bytes)를 사용할 경우, 레지스터에 들어가는 데이터 크기가 2배가 되므로 Lane 수는 정확히 절반으로 줄어들며 전체 Throughput도 반감됩니다.

| ISA | 레지스터 폭 | float32 lane | 비고 |
| :--- | :--- | :--- | :--- |
| **SSE** | 128 bit | 4 | x86 모든 현대 CPU 지원 |
| **AVX2** | 256 bit | **8** | Intel Haswell+ / AMD Zen+ 이상 |
| **AVX-512** | 512 bit | 16 | 서버급, 일부 데스크탑 |
| **NEON** | 128 bit | 4 | ARM (Apple Silicon, 모바일) |

### 1.3 Peak GFLOPS 공식
CPU 코어가 초당 수행할 수 있는 최대 부동소수점 연산 횟수를 계산하는 공식입니다.

$$\text{Peak GFLOPS} = \text{Clock(GHz)} \times \text{SIMD\_Lane} \times \text{FMA\_Factor}$$

* **FMA_factor**: FMA(Fused Multiply-Add) 지원 시 2를 적용합니다.
* **예시 계산**:
    * 3 GHz &times; AVX2 (8 lane) &times; FMA(2) &rarr; 48 GFLOPS / core
    * 8 코어 모두 사용 시 &rarr; **~384 GFLOPS**

---

## 2. Python 루프와 SIMD의 관계

### 2.1 왜 Python 루프는 SIMD를 못 쓰는가?
Python 인터프리터 환경에서는 다음과 같은 이유로 하드웨어의 SIMD 기능을 직접 활용하기 어렵습니다.

1. **인터프리터 오버헤드**: 인터프리터가 요소를 하나씩 꺼내어 처리(dispatch)합니다.
2. **PyObject 오버헤드**: 각 요소가 순수 데이터가 아닌 거대한 PyObject(참조, 타입 체크, refcount 등 포함)로 취급됩니다.
3. **최적화 부재**: 런타임 해석의 특성상 SIMD 명령어를 생성(emit)할 구조적 자리가 없습니다.
4. **해결책**: NumPy는 C/Fortran으로 컴파일된 **BLAS(Basic Linear Algebra Subprograms)** 라이브러리를 호출하여 그 내부에서 하드웨어 레벨의 SIMD를 수행합니다.

### 2.2 성능 분해 (Performance Decomposition)
단순 연산에서 발생하는 약 **700배**의 성능 차이는 다음과 같은 요인들로 분해할 수 있습니다.
* **캐시(Cache)**: 연속된 메모리 접근으로 인한 가속 (~3x)
* **SIMD**: 벡터 명령어를 통한 병렬 처리 (~4x)
* **인터프리터**: 루프 및 박싱 오버헤드 제거 (~60x)
* **종합**: **3 &times; 4 &times; 60 &approx; 700x** 가속

---

## 3. 이론적 Peak vs 실측 활용률 분석

### 3.1 실험 의도
본인 CPU의 이론적 Peak GFLOPS를 계산하고, NumPy `MatMul`로 실제 도달 성능(Throughput)을 측정하여 **활용률(Utilization)** 을 도출합니다. SIMD 연산력이 아무리 높아도 메모리 대역폭이 이를 뒷받침하지 못하면 병목(Memory Wall)이 발생할 수 있습니다.

### 3.2 하드웨어별 검증 기준
* **일반 (Intel/AMD)**: 측정 GFLOPS가 이론치의 **30~70%** 범위 내에 위치하면 정상입니다.
* **Apple Silicon (M-class)**: 활용률이 **100%를 초과**(예: 1500%)하는 현상이 나타납니다.
    * **원인**: Apple Matrix Coprocessor(**AMX**)가 BLAS 연산을 가속하기 때문입니다.
    * **분석**: 표준 벡터 Lane 공식이 거대한 매트릭스 엔진의 Throughput을 모두 설명하지 못해 발생하는 현상으로, 지극히 정상적인 결과입니다.

---

## 4. 벡터 연산 변형 비교 (Vector Add)

동일한 $1,000,000(1M)$ 길이의 두 벡터 덧셈 연산을 세 가지 방식으로 수행하여 성능을 측정합니다.

| 변형 | 데이터 타입 | 실행 방식 | 핵심 포인트 |
| :--- | :--- | :--- | :--- |
| **(a)** | Python list | `[a[i] + b[i] for i in range(N)]` | 1-1 베이스라인 |
| **(b)** | NumPy 배열 | `for i: c[i] = a[i] + b[i]` | **Surprise!** Python 루프 사용 시 오히려 지연 발생 |
| **(c)** | NumPy 배열 | `c = a + b` (벡터화) | NumPy 본연의 고속 연산 |

* **결과 정합성**: 모든 결과는 `np.allclose`를 통해 허용 오차 내 일치 여부를 검증합니다.
* **성능 특징**: 환경에 따라 (b)가 (a)보다 2~3배 느릴 수 있는데, 이는 데이터를 넣고 빼는 **NumPy boxing overhead** 때문입니다.

---

## 5. CPU vs GPU 아키텍처 토의

하드웨어 설계 목적에 따른 구조적 차이를 Lane 관점에서 분석합니다.

| 항목 | CPU | GPU |
| :--- | :--- | :--- |
| **Lane 수** | 4 ~ 16 | **32 ~ 수천** (warp &times; SM) |
| **1 코어 성격** | scalar + 약간의 SIMD | **거대한 SIMD 머신 (SM)** |
| **강점** | 레이턴시(latency), 복잡한 분기 처리 | **처리량(throughput)**, 대규모 병렬 연산 |

---

## 6. 흔한 막힘 포인트 (Troubleshooting)

| 증상 | 원인 | 해결책 |
| :--- | :--- | :--- |
| `py-cpuinfo` 설치 안 됨 | venv 활성화 누락 | `source .venv/bin/activate && pip install py-cpuinfo` |
| **(b)가 (a)보다 훨씬 느림 (2-5x)** | NumPy scalar boxing overhead | **정상**. NumPy 배열도 Python 루프면 느림을 인지 |
| **GFLOPS > 이론 Peak** | 매트릭스 코프로세서 존재 (AMX 등) | **정상**. 1-4 실습에서는 실측 Peak를 기준으로 사용 |
| **클럭/FMA 검출 실패** | `py-cpuinfo` 인식 한계 (Apple Silicon) | 단순 공식의 한계를 인지하는 학습 자료로 활용 |
| **활용률 5% 미만** | BLAS가 Single-threaded로 동작 | `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` 확인 |

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 문서에서 다룬 Peak GFLOPS 및 성능 분해 이론을 실제로 검증하는 파이썬 벤치마크 코드는 [03_simd_bench.py](../lab/03_simd_bench.py)에서 확인하실 수 있습니다.
* **분석 보고서 (Analysis)**: 위 실습 코드를 실행하여 얻은 구체적인 측정 데이터와 아키텍처별 예외 상황(AMX 개입 등)에 대한 심층 분석은 [03_simd_execution_report.md](./03_simd_execution_report.md)에 상세히 기록되어 있습니다.

### 2. 향후 확장 가능성 (Future Scope)
본 장에서 다룬 **SIMD 벡터화 기술**은 단일 코어의 성능 한계를 끌어내는 기초가 됩니다. 다음 단계인 `04_system_optimization` 과정에서는 다중 코어를 활용하는 **멀티스레딩(Multi-threading)** 및 캐시 효율을 극대화하는 **Tiling 기법**과 결합되어, 하드웨어의 활용률을 극한으로 밀어붙이는 최적화 패턴의 기반 지식으로 활용될 예정입니다.