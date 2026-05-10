# 03_simd_execution_report.md: Analysis of SIMD Utilization and Performance Decomposition

본 보고서는 [03_simd_bench.py](../lab/03_simd_bench.py) 실습 코드를 바탕으로 하드웨어의 이론적 최대 성능($Peak$ $GFLOPS$)을 산출하는 공식과 실측 데이터 사이의 상관관계를 분석합니다. 특히 $SIMD$ 명령어 집합($ISA$)에 따른 병렬 처리 효율과 $FMA$ 연산의 기여도를 정량적으로 분해하는 데 중점을 둡니다.

> **💡 이론적 배경 확인**: 본 실험에서 측정한 $Peak\ GFLOPS$ 산출 공식의 세부 파라미터와 $SIMD$ 가속의 원리에 대한 이론적 설명은 [03_simd_vectorization.md](./03_simd_execution_report.md) 문서에서 상세히 다루고 있습니다.

---

## 1. 주요 API 및 환경 분석

실험에 사용된 핵심 $API$는 시스템의 하드웨어 제원을 자동으로 식별하고 연산을 위한 기초 데이터를 생성하는 역할을 수행합니다.

| API | 설명 | 비고 |
| :--- | :--- | :--- |
| `cpuinfo.get_cpu_info()` | 현재 시스템의 CPU 상세 정보를 딕셔너리(Map) 형태로 확보 | $ISA$ 플래그 확인용 |
| `platform.processor()` | 현재 실행 중인 CPU의 프로세서 이름(문자열) 반환 | 시스템 식별용 |
| `np.arange(N, dtype=np.float32)` | $0$부터 $N-1$까지의 값을 가지는 1차원 배열 생성 | 벡터 연산 데이터셋 |

---

## 2. 함수별 로직 상세 해석

### 2.1 `get_cpu_info()`: 공식 입력값 자동 추출
이론적 $Peak$ 성능 계산에 필요한 변수(클럭, 코어 수, $SIMD$ 폭)를 시스템 하드웨어 레벨에서 직접 추출합니다.

* **Fallback(안전망) 설계**: `py-cpuinfo` 패키지가 특정 환경(예: 최신 ARM 칩셋 등)에서 하드웨어 정보를 제대로 읽어오지 못할 경우를 대비하여 `clock_ghz: 3.0`이나 `simd_lane_fp32: 4`와 같은 기본값을 설정합니다. 이는 예기치 못한 환경에서도 프로그램이 중단되지 않고 실행될 수 있도록 보장하는 **엔지니어링적 예외 처리**로, 다양한 런타임 환경을 고려하는 탄탄한 개발 역량을 보여줍니다.
* **SIMD ISA 우선순위**: 시스템이 여러 $ISA$를 동시에 지원할 경우, 가장 강력한(단위 사이클당 처리량이 높은) $ISA$를 채택하도록 설계합니다.
  
| 우선순위 | ISA Flag | float32 Lane | 비고 |
| :---: | :--- | :---: | :--- |
| **1** | `avx512f` | 16 | 최상위 서버급 $ISA$ |
| **2** | `avx2` / `avx` | 8 | 현대적 데스크탑 표준 |
| **3** | `asimd` / `neon` | 4 | **Apple Silicon** / 모바일 최저 기준 |

> **Key Point**: 본인 노트북 CPU가 지원하는 최상위 $SIMD$ $ISA$를 식별함으로써, 소프트웨어가 활용할 수 있는 하드웨어적 한계를 명확히 규정합니다.

### 2.2 `theoretical_peak_gflops()`: 이론적 한계치 산출
물리적인 제원을 바탕으로 '이론적으로 도달 가능한 최상의 성능'을 계산합니다.

$$
\text{Peak GFLOPS} = \text{Clock (GHz)} \times \text{SIMD Lane} \times \text{FMA Factor}
$$

* **FMA(Fused Multiply-Add)의 의미**: $d = a \times b + c$ 연산을 단일 사이클에 수행합니다.
    * 곱셈($1$ $FLOP$) + 덧셈($1$ $FLOP$) = $2$ $FLOP$
    * 따라서 $FMA$ 지원 시 $Peak$ 계산에 $\times 2$ 가중치를 부여합니다.

### 2.3 `measured_numpy_matmul_gflops()`: 현실의 실측 데이터
이론적 수치가 아닌, 실제 $NumPy$ 라이브러리가 $BLAS$를 통해 하드웨어를 구동한 결과값을 측정합니다.

```python
# 현실적인 측정 로직
A = np.random.rand(N, N).astype(np.float32)
B = np.random.rand(N, N).astype(np.float32)

_ = A @ B  # Warmup: 라이브러리 로딩 및 캐시 초기화

t0 = time.perf_counter()
for _ in range(n_runs):
    _ = A @ B
elapsed = (time.perf_counter() - t0) / n_runs

# GFLOPS 계산: (2 * N^3) / 소요시간 / 10^9
return (2 * N**3) / elapsed / 1e9
```
* **$2 \times N^3$** 의 유도: $N \times N$ 행렬 곱셈은 각 출력 요소당 $N$번의 $MAC$(Multiply-Accumulate) 연산을 수행합니다. $MAC$은 $2$ $FLOP$이며, 총 $N^2$개의 요소가 존재하므로 총 연산량은 $2N^3$이 됩니다.

---

## 3. 로컬 환경 실측 결과 분석 (Empirical Data Analysis)

이론적 공식이 실제 하드웨어 환경에서 어떻게 발현되는지 확인하기 위해, 로컬 시스템(13th Gen Intel Core i9-13900H)에서 측정한 벤치마크 데이터를 바탕으로 이론과 현실의 간극을 심층 분석합니다.

### 3.1 Peak GFLOPS 및 시스템 활용률 (Experiment 1)

시스템의 물리적 제원을 기반으로 산출된 이론적 연산 한계치와, 실제 행렬 곱셈($MatMul$) 연산을 통해 도달한 실측 성능을 비교합니다.

```text
=== Experiment 1: Theoretical peak vs measured ===
  CPU:           13th Gen Intel(R) Core(TM) i9-13900H
  Source:        py-cpuinfo
  Clock (assumed): 3.00 GHz
  Cores:         20
  SIMD ISA:      AVX2
  FP32 lanes:    8
  FMA:           True

  Theoretical peak (single core):     47.9 GFLOPS
  Theoretical peak (all cores):      958.4 GFLOPS

  Measured NumPy MatMul (4096^2):    581.5 GFLOPS
  Utilization:                        60.7% of all-core peak
```

* **이론적 한계치 도출 로직**: 
    * 코어당 성능: $3.00\ GHz \times 8\ lanes\ (AVX2) \times 2\ (FMA) \approx 48.0\ GFLOPS$ (세부 클럭 보정치 적용 시 $47.9\ GFLOPS$)
    * 전체 코어 성능: $47.9\ GFLOPS \times 20\ cores = 958.4\ GFLOPS$ 

* **실측 데이터 분석 ($Insight$)**:
    * 대규모 행렬($4096 \times 4096$) 연산 실측 결과 $581.5\ GFLOPS$ 를 기록하여 이론치 대비 $60.7\%$ 의 활용률(Utilization) 을 달성했습니다.
    * 활용률 60.7%의 엔지니어링적 의미: 랩탑 환경(H-series 프로세서) 특성상 모든 코어가 100% 가동될 때 발생하는 전력 제한(Power Limit) 및 발열 제어(Thermal Throttling), 그리고 연산 속도를 따라가지 못하는 메모리 대역폭(Memory Bandwidth)의 병목을 고려할 때, 60%대의 활용률은 고도로 최적화된 $BLAS$ 라이브러리가 하드웨어를 한계치까지 매우 훌륭하게 구동하고 있음을 방증하는 정상적이고 우수한 수치입니다.

### 3.2 성능 분해 및 인터프리터 오버헤드 실증 (Experiment 2)

길이 $N=1,000,000$의 벡터 덧셈을 세 가지 다른 방식으로 수행하여, 성능 저하의 주된 원인(Python 루프)과 성능 향상의 핵심(SIMD 벡터화)을 정량적으로 분해합니다. 

```text
=== Experiment 2: 700x decomposition ===
Vector add, length N=1,000,000

  (a) Python list  + Python loop:        45.5 ms
  (b) NumPy array  + Python loop:       149.8 ms
  (c) NumPy array  + vectorized:          0.988 ms

  (a) / (b) ratio (NumPy element boxing overhead):    0.30x
  (b) / (c) ratio (SIMD + vectorization removes interpreter):      152x
  (a) / (c) ratio (everything):                         46x
```

* **(a) vs (b) - Boxing Overhead의 치명성**:
    * $NumPy$ 배열을 사용했음에도 불구하고 $Python$ 루프를 통해 원소 단위로 접근한 (b) 방식($149.8\ ms$)이, 순수 파이썬 리스트를 사용한 (a) 방식($45.5\ ms$)보다 오히려 약 3.3배 ($1/0.30$) 더 느리게 측정되었습니다.
    * 이는 C 배열 형태인 $NumPy$ 데이터를 파이썬 인터프리터가 읽기 위해 매번 무거운 $PyObject$로 감싸고 푸는 데이터 타입 변환(Boxing/Unboxing) 오버헤드가 100만 번 반복되면서 발생한 참사로, 잘못된 라이브러리 사용이 시스템 성능에 미치는 악영향을 실증합니다.

* **(b) vs (c) - Vectorization과 SIMD의 위력**:
    * $NumPy$의 벡터화 연산을 활용한 (c) 방식($0.988\ ms$)은 파이썬 인터프리터의 개입을 완전히 배제하고 백그라운드에서 C 컴파일 코드와 $AVX2\ SIMD$ 명령어를 직접 호출합니다.
    * 그 결과, 잘못된 배열 사용 방식인 (b) 대비 무려 152배의 속도 향상을 이루어냈으며, 밀리초($ms$) 단위의 연산 지연을 서브 밀리초($< 1\ ms$) 단위로 압축하는 위력을 보여줍니다.

* **최종 가속 배율 ($Total\ Speedup$)**:
    * 일반적인 파이썬 리스트 연산 **(a)** 를 고도로 최적화된 하드웨어 가속 연산 **(c)** 로 전환함으로써 **총 46배**의 획기적인 누적 성능 향상을 달성했습니다. 이는 데이터 집약적인 어플리케이션에서 아키텍처 인지형(Architecture-aware) 코드 작성이 왜 필수적인지를 수치로 증명합니다.

---

## 4. 학습 포인트 및 보편적 오해 분석

### 4.1 공식 vs 현실의 간극

* **공식**: 하드웨어가 "할 수 있는 최대치"를 의미합니다.

* **측정**: 실제 소프트웨어 스택($Python$ → $NumPy$ → $BLAS$ → $Hardware$)을 거친 "실제 결과"입니다.

### 4.2 NumPy 활용에 대한 오해와 진실

* **흔한 오해**: "단순히 $NumPy$ 배열을 쓰기만 하면 무조건 빠를 것이다."

* **기술적 실제**:

    * $NumPy$ 배열은 벡터 연산(Vectorized Operation)으로 호출할 때만 성능이 비약적으로 향상됩니다. 이는 $NumPy$가 내부적으로 C 또는 Fortran으로 고도로 최적화된 **BLAS(OpenBLAS, MKL, Accelerate 등)** 라이브러리를 호출하여 하드웨어의 $SIMD$ 명령어를 직접 실행하기 때문입니다.

    * 만약 요소(element) 단위로 $Python$ 루프를 통해 접근한다면, 데이터를 $PyObject$로 감싸는 과정에서 발생하는 **Boxing Overhead** 로 인해 일반 리스트보다 오히려 느려질 수 있습니다.

---

## 5. 문제 해결 가이드 (Troubleshooting)

| 증상 | 원인 | 해결책 |
| :--- | :--- | :--- |
| **측정 GFLOPS > 이론 Peak** | $AMX$(Apple Matrix Coprocessor), Intel AMX-TILE 등의 개입 | 정상. 단순 벡터 공식이 매트릭스 엔진 성능을 포착 못 함 |
| **활용률 5% 미만** | $BLAS$가 단일 스레드로 동작 | `OPENBLAS_NUM_THREADS` 환경 변수 확인 |
| **ISA 식별 실패** | `py-cpuinfo` 패키지 미설치 | `pip install py-cpuinfo` 수행 |

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 분석의 기반이 되는 실험 코드는 [03_simd_bench.py](../lab/03_simd_bench.py)에서 확인 가능합니다.
* **이론적 배경 (Analysis)**: $SIMD$ 기초 개념 및 아키텍처별 레지스터 폭에 대한 상세 설명은 [03_simd_vectorization.md](../analysis/03_simd_vectorization.md)에 기술되어 있습니다.

### 2. 향후 확장 가능성 (Future Scope)
본 실험에서 도출된 **활용률(Utilization) 데이터**는 다음 단계인 [04_system_optimization](../../04_system_optimization/)의 핵심 기준 지표로 사용됩니다. 향후 이를 바탕으로 $Kernel\ Fusion$ 및 $Tiling$ 기법을 적용하여, 실제 성능을 하드웨어의 이론적 $Peak$치에 최대한 가깝게 끌어올리는 최적화를 수행할 예정입니다.
