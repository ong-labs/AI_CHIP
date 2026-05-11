# 04_performance_modeling.md: Performance Modeling & Bottleneck Mastery

이 문서는 [04_roofline_report.md](../analysis/04_roofline_report.md)에서 다룬 Roofline 모델 이론과 [04_roofline_bench.py](../lab/04_roofline_bench.py) 실습을 통해 얻은 실측 데이터를 바탕으로 구성되었습니다. 하드웨어의 물리적 한계치 내에서 워크로드의 성격(Arithmetic Intensity)을 규정하고, 성능 병목의 근본 원인을 분석하는 역량을 검증합니다.

---

## 📝 개념 확인 문제 (Quiz)

### 문제 1. Memory Bound의 정의

* **질문:** 다음 중 Memory Bound 상황에 가장 가까운 것은?
* **정답: B. 계산은 거의 없지만 엄청난 양의 데이터를 계속 읽는다**
* **해설:** Memory Bound는 연산기의 처리 능력보다 데이터를 실어 나르는 메모리 대역폭(Bandwidth)의 속도가 느려 성능이 제한되는 상황을 의미합니다.

### 문제 2. Arithmetic Intensity(AI)의 의미

* **질문:** Arithmetic Intensity(AI)가 높다는 의미로 가장 적절한 것은?
* **정답: B. 데이터를 읽은 뒤 많은 계산을 수행한다**
* **해설:** AI는 메모리에서 읽어온 데이터 1바이트당 수행하는 부동소수점 연산의 횟수를 의미하며, 식으로는 아래와 같습니다.
$$AI = \frac{FLOPs}{Bytes}$$


### 문제 3. 행렬곱의 병목 특성

* **질문:** 행렬곱(Matrix Multiplication)이 일반적으로 Compute-bound인 이유는?
* **정답: B. 같은 데이터를 여러 번 재사용하며 계산량이 많기 때문**
* **해설:** 행렬곱은 $O(N^3)$의 연산량 대비 $O(N^2)$의 데이터 접근량을 가지므로, 데이터 재사용성(Reuse Factor)과 AI가 매우 높아 연산 성능이 주된 병목이 됩니다.

### 문제 4. Cache Reuse의 효과

* **질문:** Cache reuse가 증가하면 일반적으로 어떤 효과가 발생하는가?
* **정답: A. 메모리 접근량 감소**
* **해설:** 데이터를 캐시 내에서 반복적으로 재사용하면 외부 메모리(DRAM)까지 데이터를 가지러 가는 횟수가 줄어들어 실질적인 대역폭 소모를 절약할 수 있습니다.

### 문제 5. Roofline 모델의 핵심 목적

* **질문:** Roofline Model의 핵심 목적은?
* **정답: C. 성능 병목이 계산인지 메모리인지 분석하기 위해**
* **해설:** 하드웨어의 최대 연산 성능과 메모리 대역폭을 두 축으로 하여, 현재 워크로드의 성능을 결정짓는 물리적 한계가 무엇인지 시각화하고 진단하는 것이 목적입니다.

### 문제 6. Theoretical Peak FLOPS 계산

* **질문:** 다음 CPU의 theoretical peak FLOPS는? (Clock: 3 GHz, SIMD width: 8, FMA 지원)
* **정답: B. 48 GFLOPS**
* **해설:** FMA(Fused Multiply-Add)는 한 사이클에 곱셈과 덧셈을 동시에 처리하므로 2 FLOPs로 계산합니다. 
공식은 다음과 같습니다.
$$3 \times 8 \times 2 = 48$$



### 문제 7. Arithmetic Intensity 산출 실습

* **질문:** 어떤 연산이 다음과 같을 때 Arithmetic Intensity(AI)는? (연산량: 200 GFLOPs, 메모리 접근량: 50 GB)
* **정답: C. 4**
* **해설:** 
$$AI = \frac{200 \text{ GFLOPs}}{50 \text{ GB}} = 4 \text{ FLOPs/byte}$$


### 문제 8. 워크로드 병목 예측

* **질문:** Peak Compute가 10 TFLOPS이고 Memory Bandwidth가 200 GB/s인 GPU에서, AI가 0.5인 워크로드의 병목은?
* **정답: B. Memory Bound**
* **해설:** 해당 기기의 임계 AI(Critical AI)는 워크로드의 AI(0.5)가 임계치(50)보다 현저히 낮으므로 메모리 속도가 연산을 따라가지 못하는 상황입니다.
$$10,000 / 200 = 50$$


### 문제 9. 메모리 레이턴시 분석

* **질문:** 다음 Pointer chasing 결과에서 Cache miss가 급증하기 시작한 구간은? (256 KB → 145 ns, 1 MB → 228 ns)
* **정답: C. 256 KB ~ 1 MB 부근**
* **해설:** 레이턴시가 급격히 상승하는 구간은 데이터 셋의 크기가 특정 캐시(L2 또는 L3)의 용량을 초과하여 하위 계층 메모리(DRAM)로 접근이 전이되는 지점입니다.

### 문제 10. 성능 최적화의 방향성

* **질문:** 다음 중 현대 고성능 컴퓨팅에서의 성능 최적화 방향으로 가장 적절한 것은?
* **정답: B. cache reuse 증가**
* **해설:** 연산기의 속도보다 메모리 대역폭의 성장이 느린 현대 컴퓨팅 아키텍처에서는, 데이터를 최대한 연산기 근처(Cache)에 머물게 하여 메모리 접근을 최소화하는 것이 가장 효과적인 최적화입니다.

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)

* **실습 소스 코드 (Lab)**: 본 퀴즈에서 다룬 Roofline 예측 및 CPU/GPU 파라미터 시뮬레이션은 [04_roofline_bench.py](../lab/04_roofline_bench.py)를 통해 재현 가능합니다.
* **분석 보고서 (Analysis)**: AI/HPC 환경에서 행렬곱이 중요한 이유와 Reuse Factor의 위력에 대한 심층 분석은 [04_roofline_report.md](../analysis/04_roofline_report.md)에 기록되어 있습니다.

### 2. 성능 모델의 한계와 실측

* 이론적 모델(Predicted)과 실제 측정값(Measured) 사이의 간극(예: Ratio 0.18x)은 소프트웨어 스택의 오버헤드와 하드웨어 활용률을 나타내는 중요한 데이터입니다. 이를 통해 단순 스펙 비교를 넘어 실제 가동 효율을 파악할 수 있습니다.

### 3. 향후 학습 방향

* 본 장에서 병목의 원인을 파악했다면, 다음 단계에서는 이를 극복하기 위한 커널 퓨전(Kernel Fusion), 타일링(Tiling), 그리고 아키텍처별 전용 가속기(AMX, Tensor Core) 활용을 통해 활용률을 극대화하는 과정을 다룹니다.