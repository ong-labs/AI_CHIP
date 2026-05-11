# 01_system_foundations: AI Computing & System Architecture

이 폴더는 AI 반도체 설계 및 소프트웨어 가속의 핵심 기반인 **연산(Computation)** 과 **메모리(Memory)** 의 관계를 다룹니다. [analysis](./analysis), [lab](./lab), [mastery](./mastery)로 이어지는 단계별 학습을 통해 하드웨어 인지적(Hardware-aware) 프로그래밍 역량을 배양합니다.

---

## 📂 저장소 워크플로우 (A-L-M)

본 저장소는 엔지니어링 표준 사이클을 따라 구성되어 있습니다.

1.  **analysis**: 시스템 아키텍처 및 연산 원리에 대한 이론적 분석
2.  **lab**: 분석한 가설을 실제 코드로 구현하고 데이터를 수집하는 실습 단계
3.  **mastery**: 수집된 데이터를 해석하고 지식의 무결성을 검증하는 숙달 단계

---

## 📝 커리큘럼 로드맵

### Unit 1. 행렬 곱셈 연산과 실행 계층 분석
AI 연산의 기초인 MatMul을 통해 소프트웨어 인터프리터 오버헤드와 하드웨어 가속(SIMD)의 차이를 이해합니다.

* **[analysis]** [01_matmul_execution_report.md](./analysis/01_matmul_execution_report.md): 실행 계층에 따른 성능 차이 분석
* **[lab]** [01_matmul_bench.py](./lab/01_matmul_bench.py): Python Loop vs NumPy Vectorization 성능 측정
* **[mastery]** [01_performance.md](./mastery/01_performance.md): 연산 복잡도 및 GFLOPs 지표 검증

### Unit 2. 메모리 계층 구조와 지연 시간 프로파일링
메모리 지연 시간(Latency)을 직접 측정하여 캐시 지역성(Locality)이 성능에 미치는 치명적인 영향을 분석합니다.

* **[analysis]** [02_memory_subsystem.md](./analysis/02_memory_subsystem.md): 캐시 위계 및 메모리 접근 패턴 이론
* **[analysis]** [02_cache_hierarchy_report.md](./analysis/02_cache_hierarchy_report.md): API 활용 및 메모리 계층 동역학 실측 보고서
* **[lab]** [02_cache_hierarchy_bench.py](./lab/02_cache_hierarchy_bench.py): Pointer Chasing을 통한 레이턴시 실측
* **[result]** [02_working_set_result.png](./lab/results/02_working_set_result.png): 하드웨어별 메모리 워킹셋 측정 그래프
* **[mastery]** [02_memory_latency.md](./mastery/02_memory_latency.md): 캐시 미스 및 공간/시간 지역성 개념 숙달

### Unit 3. SIMD 병렬 연산과 하드웨어 가속
현대 CPU의 핵심 병렬화 기술인 SIMD의 원리를 이해하고, 하드웨어의 이론적 최대 성능(Peak GFLOPS)과 실측 성능의 간극을 분석합니다.

* **[analysis]** [03_simd_vectorization.md](./analysis/03_simd_vectorization.md): SIMD 가속 원리 및 아키텍처별 레지스터 폭 분석
* **[analysis]** [03_simd_execution_report.md](./analysis/03_simd_execution_report.md): 하드웨어 활용률 및 700배 성능 분해 실측 보고서
* **[lab]** [03_simd_bench.py](./lab/03_simd_bench.py): SIMD Peak GFLOPS 및 성능 가속 배율 측정 실습
* **[mastery]** [03_parallel_computing.md](./mastery/03_parallel_computing.md): SIMD 활용 및 병렬 연산 핵심 개념 숙달

### Unit 4. Roofline 모델과 성능 병목 분석
하드웨어의 물리적 한계(Peak GFLOPS, BW)와 알고리즘의 연산 밀도(AI)를 결합하여 성능 병목을 정량적으로 진단합니다.

* **[analysis]** [04_roofline_model.md](./analysis/04_roofline_model.md): Roofline 이론 및 Arithmetic Intensity(AI) 분석
* **[analysis]** [04_roofline_report.md](./analysis/04_roofline_report.md): CPU 실측 및 GPU 예측 성능 비교 보고서
* **[lab]** [04_roofline_bench.py](./lab/04_roofline_bench.py): 파라미터 기반 성능 시뮬레이터 구현 및 검증
* **[mastery]** [04_performance_modeling.md](./mastery/04_performance_modeling.md): 성능 모델링 및 병목 지점 판별 숙달

---

## 🏗️ Directory Structure
```text
01_system_foundations/
├── README.md
├── analysis/
│   ├── 01_matmul_execution_report.md  # 행렬 곱셈 연산 분석 리포트
│   ├── 02_cache_hierarchy_report.md   # 캐시 위계 실측 보고서
│   ├── 02_memory_subsystem.md         # 메모리 계층 및 접근 패턴 이론 정리
│   ├── 03_simd_execution_report.md    # SIMD 활용 및 성능 분해 보고서
│   ├── 03_simd_vectorization.md       # SIMD 가속 이론 및 ISA 분석
│   ├── 04_roofline_model.md           # Roofline 이론 및 AI 분석
│   └── 04_roofline_report.md          # 성능 병목 실측 분석 보고서
├── lab/
│   ├── results/                       # 실험 결과 데이터 및 시각화 지표
│   │   └── 02_working_set_result.png 
│   ├── 01_matmul_bench.py             # 연산 성능 벤치마크 코드
│   ├── 02_cache_hierarchy_bench.py    # 메모리 레이턴시 측정 코드
│   ├── 03_simd_bench.py               # SIMD 성능 측정 및 분해 코드
│   └── 04_roofline_bench.py           # Roofline 기반 성능 시뮬레이터
└── mastery/
    ├── 01_performance.md              # 성능 분석 핵심 개념 요약
    ├── 02_memory_latency.md           # 메모리 계층 숙달 퀴즈 및 정리
    ├── 03_parallel_computing.md       # 병렬 연산 숙달 퀴즈
    └── 04_performance_modeling.md     # 성능 모델링 및 병목 판별 숙달

```
---
*본 저장소는 하드웨어 인지적 최적화의 통찰을 추구하며, 모든 실습 데이터는 검증되었습니다.*