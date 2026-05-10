# 03_parallel_computing.md: SIMD & Parallel Acceleration Mastery

이 문서는 [03_simd_vectorization.md](../analysis/03_simd_vectorization.md)에서 다룬 병렬 연산 이론과 [03_simd_execution_report.md](../analysis/03_simd_execution_report.md)의 실측 데이터를 바탕으로 구성되었습니다. 현대 CPU의 SIMD(Single Instruction Multiple Data) 활용 능력과 하드웨어 성능의 한계치(Peak GFLOPS)를 정량적으로 분석하고 검증하는 역량을 테스트합니다.

## 개념 확인 문제 (Quiz)

### 문제 1. SIMD의 정의

* **질문:** 다음 중 SIMD에 대한 설명으로 가장 적절한 것은?
* **정답: B. 여러 데이터를 하나의 명령어로 동시에 처리한다**
* **해설:** SIMD는 **Single Instruction Multiple Data**의 약자로, 하나의 명령어가 레지스터 내의 여러 데이터 'Lane'에 동시에 적용되어 연산 효율을 극대화하는 기술입니다.

### 문제 2. AVX2의 처리량

* **질문:** AVX2에서 float32 연산 시 한 사이클에 처리 가능한 데이터 개수는?
* **정답: B. 8**
* **해설:** AVX2는 **256-bit** 레지스터를 사용합니다. 단정밀도 부동소수점(`float32`)은 4바이트(32-bit)이므로, $256 \div 32 = 8$개의 데이터를 동시에 처리할 수 있습니다.

### 문제 3. Peak GFLOPS 계산

* **질문:** 다음 CPU의 single-core peak GFLOPS는? (Clock: 3 GHz, SIMD lane: 8, FMA 지원)
* **정답: B. 48**
* **해설:** 공식에 따라 $3\text{ GHz} \times 8\text{ lanes} \times 2\text{ (FMA)} = 48\text{ GFLOPS}$가 산출됩니다.

### 문제 4. FMA Factor의 의미

* **질문:** Peak GFLOPS 공식에서 FMA factor가 2가 되는 이유는?
* **정답: B. 곱셈과 덧셈을 한 사이클에 수행하기 때문**
* **해설:** FMA(Fused Multiply-Add)는 $a \times b + c$ 연산을 하나의 사이클에 처리합니다. 곱셈과 덧셈이라는 두 개의 부동소수점 연산을 한 번에 수행하므로 연산량을 2배로 계산합니다.

### 문제 5. 연산 방식별 성능 비교

* **질문:** 다음 중 가장 빠른 연산 방식은?
* **정답: C. NumPy array + vectorized 연산 (a + b)**
* **해설:** 벡터화된 연산은 Python 인터프리터를 거치지 않고 내부적으로 최적화된 C/C++ 및 SIMD 명령어를 직접 호출하므로 가장 빠릅니다.

### 문제 6. NumPy와 Python Loop

* **질문:** NumPy 배열을 사용했는데도 Python loop를 사용하면 느린 이유는?
* **정답: B. Python 인터프리터가 element 단위로 실행하기 때문**
* **해설:** 배열 자체는 NumPy일지라도 루프를 Python에서 돌리면 매 원소마다 **Boxing/Unboxing(데이터 타입 변환)** 오버헤드가 발생하며, SIMD의 이점을 전혀 활용하지 못합니다.

### 문제 7. 성능 가속의 3대 요인

* **질문:** 다음 중 성능 차이를 만드는 3가지 주요 요인에 해당하지 않는 것은?
* **정답: D. GPU 사용 여부**
* **해설:** 본 실습에서 분석한 700배의 성능 격차는 **캐시(지역성), SIMD(병렬성), 인터프리터 오버헤드 제거**라는 세 가지 하드웨어/소프트웨어적 요인의 결합으로 발생합니다.

### 문제 8. CPU vs GPU 아키텍처

* **질문:** CPU와 GPU의 가장 본질적인 차이를 lane 관점에서 설명하면?
* **정답: B. CPU는 scalar 중심, GPU는 massive SIMD 구조**
* **해설:** CPU는 복잡한 제어 로직과 빠른 레이턴시 중심의 적은 수의 Lane을 가지지만, GPU는 단순한 연산 유닛 수천 개가 거대한 SIMD(또는 SIMT) 구조를 이루어 처리량(Throughput)을 극대화합니다.

### 문제 9. NumPy의 가속 원리 (서술형)

* **질문:** NumPy의 `A @ B`가 Python loop보다 수백 배 빠른 이유를 **SIMD, 캐시, 인터프리터** 키워드를 사용해 설명하라.
* **정답: NumPy는 내부적으로 C/BLAS를 통해 Python 인터프리터 오버헤드 없이 기계어 레벨에서 직접 실행되며, SIMD 명령어를 사용해 여러 데이터를 병렬로 처리하고, 연속된 메모리 배치를 통해 캐시 지역성을 극대화하기 때문입니다.**

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 퀴즈에서 다룬 수치 데이터와 성능 분해 로직은 [03_simd_bench.py](../lab/03_simd_bench.py)를 통해 직접 구동하고 재현할 수 있습니다.
* **이론 및 리포트 (Analysis)**: 각 ISA별 레지스터 명세와 60.7% 활용률에 대한 하드웨어적 제약 사항 분석은 [03_simd_vectorization.md](../analysis/03_simd_vectorization.md)와 [03_simd_execution_report.md](../analysis/03_simd_execution_report.md)에 상세히 기술되어 있습니다.

### 2. 정밀도(Precision)와 성능의 상관관계
* 실습에서 사용된 `float32` 대비 `float64`(배정밀도)를 사용하면 Lane 폭이 절반으로 줄어들어 성능 수치(GFLOPS)도 절반으로 감소합니다. 이는 AI 반도체 설계에서 왜 `FP16`이나 `INT8` 같은 저정밀도 연산이 선호되는지에 대한 기초적인 근거가 됩니다.

### 3. 향후 확장 가능성 (Future Scope)
* 단일 코어 내의 SIMD 활용을 넘어, 다음 단계인 [04_system_optimization](../../04_system_optimization/)에서는 다중 코어를 활용하는 **멀티스레딩**과 메모리 접근 효율을 극대화하는 **Tiling 기법**을 결합하여 실제 활용률을 Peak치에 가깝게 견인하는 최적화 과정을 다룰 예정입니다.
