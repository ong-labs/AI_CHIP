# 05_system_perf_expert.md: CPU vs GPU vs NPU Architecture Mastery

이 문서는 [05_hw_architecture_report.md](../analysis/05_hw_architecture_report.md)에서 다룬 아키텍처별 성능 분석과 [05_hw_architecture_bench.py](../lab/05_hw_architecture_bench.py) 실습을 통해 얻은 하드웨어 성능 예측 데이터를 바탕으로 구성되었습니다. CPU, GPU, 그리고 AI 특화 가속기인 NPU의 구조적 차이를 이해하고, Roofline 모델을 통한 정량적 성능 판별 역량을 검증합니다.

## 📝 개념 확인 문제 (Quiz)

### 문제 1. Roofline 모델의 실행 시간 결정 요인
* **질문:** Roofline Model에서 실제 실행 시간은 무엇으로 결정되는가?
* **정답: C. Compute Time과 Memory Time 중 더 큰 값**
* **해설:** Roofline 모델은 시스템 성능이 연산 능력(Compute)과 메모리 대역폭(Memory Bandwidth) 중 더 낮은 성능(즉, 시간이 더 오래 걸리는 쪽)에 의해 결정된다고 가정합니다 ($T = \max(T_{compute}, T_{memory})$).

### 문제 2. Compute Time의 정의
* **질문:** Compute Time은 무엇을 의미하는가?
* **정답: B. 연산 장치가 계산을 수행하는 시간**
* **해설:** 연산 시간은 총 부동소수점 연산량(FLOPs)을 하드웨어의 이론적 최대 연산 성능(Peak Performance)으로 나눈 값입니다.

### 문제 3. Memory Time의 정의
* **질문:** Memory Time은 무엇을 의미하는가?
* **정답: A. 데이터를 메모리에서 읽고 쓰는 시간**
* **해설:** 메모리 시간은 연산에 필요한 실제 데이터 전송량(Bytes)을 하드웨어의 메모리 대역폭(Bandwidth)으로 나눈 값입니다.

### 문제 4. Roofline 모델의 기본 수식
* **질문:** Roofline Model의 기본 식은 무엇인가?
* **정답: C. 실행 시간 = max(Compute Time, Memory Time)**
* **해설:** 두 제약 조건 중 병목(Bottleneck)이 되는 긴 시간을 실제 실행 시간으로 간주하는 것이 Roofline 모델의 핵심 아이디어입니다.

### 문제 5. 행렬곱의 병목 특성 원인
* **질문:** 행렬곱(Matrix Multiplication)이 주로 Compute Bound인 이유는?
* **정답: B. 데이터를 반복 재사용하여 Arithmetic Intensity가 높기 때문**
* **해설:** 행렬곱은 연산량이 데이터 전송량보다 기하급수적으로 커지는 특성이 있어, 산술 연산 밀도(AI)가 매우 높습니다. 따라서 메모리보다는 연산기 성능이 주된 병목이 됩니다.

### 문제 6. Memory Bound 작업의 예시
* **질문:** 다음 중 Memory Bound에 가까운 작업은?
* **정답: C. 배열 덧셈 (C = A + B)**
* **해설:** 배열 덧셈은 각 원소를 한 번 읽어 한 번의 연산만 수행하므로 AI가 매우 낮습니다. 따라서 연산기보다 데이터를 가져오는 메모리 속도가 성능을 결정합니다.

### 문제 7. Arithmetic Intensity(AI)의 정의
* **질문:** Arithmetic Intensity(AI)는 무엇을 의미하는가?
* **정답: B. 데이터 1바이트당 수행되는 연산량**
* **해설:** AI는 연산의 성격을 규정하는 지표로, 식으로는 다음과 같이 표현됩니다.

$$AI = \frac{FLOPs}{Bytes}$$

### 문제 8. 높은 AI의 영향
* **질문:** AI가 매우 높으면 일반적으로 어떤 상태가 되는가?
* **정답: C. Compute Bound**
* **해설:** AI가 높다는 것은 메모리에서 가져온 데이터 대비 계산량이 많다는 뜻이므로, 메모리 대역폭보다는 연산 장치의 초당 연산 한계치에 먼저 도달하게 됩니다.

### 문제 9. GPU 가속의 정량적 해석
* **질문:** CPU 대비 100배 빠른 GPU가 있다는 것은 무엇을 의미하는가?
* **정답: B. 같은 작업을 이론적으로 100배 짧은 시간에 수행할 수 있다.**
* **해설:** 가속(Speedup)은 실행 시간의 비율로 정의됩니다. 100배 빠르다는 것은 해당 아키텍처가 특정 워크로드를 처리하는 데 소요되는 시간이 CPU 대비 1/100 수준임을 의미합니다.

### 문제 10. Roofline 모델의 활용 목적
* **질문:** Roofline Model의 가장 중요한 목적은 무엇인가?
* **정답: C. 성능 병목이 계산인지 메모리인지 판단하기 위해**
* **해설:** 하드웨어의 물리적 한계와 소프트웨어의 알고리즘 특성을 결합하여, 성능 최적화를 위해 연산 성능을 높여야 하는지 대역폭을 늘려야 하는지 진단하는 도구입니다.

---

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L-M Linkage)
* **실습 소스 코드 (Lab)**: 본 퀴즈의 기반이 되는 하드웨어별 성능 예측 시뮬레이션은 [05_hw_architecture_bench.py](../lab/05_hw_architecture_bench.py)에서 확인할 수 있습니다.
* **분석 보고서 (Analysis)**: CPU, GPU, TPU, NPU 간의 정성적/정량적 차이에 대한 심층 분석 리포트는 [05_hw_architecture_report.md](../analysis/05_hw_architecture_report.md)에 기술되어 있습니다.

### 2. 하드웨어 특화의 가치 (NPU Specialization)
* NPU는 단순히 범용성을 줄인 칩이 아니라, 낮은 정밀도(INT8) 활용, 수동 메모리 관리(Scratchpad), 고정 데이터 흐름 등을 통해 AI 워크로드에서 압도적인 효율(TOPS/W)을 달성하는 장치입니다. Roofline 모델은 이러한 특화가 실제 성능 수치로 어떻게 전환되는지를 증명하는 강력한 도구입니다.