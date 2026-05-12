# npu-aware-engineering: AI Semiconductor Engineering Archive

이 저장소는 AI 반도체 설계 및 가속기 최적화의 전 과정을 체계적으로 탐구하고 기록하는 엔지니어링 아카이브입니다. 하드웨어의 물리적 한계를 이해하고, 이를 소프트웨어 계층에서 극복하기 위한 하드웨어 인지적(Hardware-aware) 최적화 방법론을 추구합니다.

---

## 📂 프로젝트 커리큘럼

본 저장소의 모든 실습은 **analysis(이론 분석) - lab(실구현 및 실험) - mastery(개념 숙달)** 의 3단계 워크플로우를 따릅니다.

### 00. [docs](./00_docs/)
AI 하드웨어 설계의 핵심 개념, 용어 사전, 공통 레퍼런스 가이드를 포함합니다. 학습 전반에 걸쳐 필요한 기초 지식 창고 역할을 수행합니다.

### 01. [system_foundations](./01_system_foundations/)
컴퓨팅 시스템의 성능 병목을 분석하는 기초를 다룹니다. 메모리 계층 구조와 캐시 효과, SIMD 병렬 처리의 원리를 학습하고, Roofline 모델을 통해 CPU와 GPU의 연산 한계를 예측하고 검증합니다.

### 02. accelerator_architecture
Google TPU의 Systolic Array 구조와 다양한 데이터 흐름(Dataflow: WS, OS, IS)을 시뮬레이션합니다. 최신 AI 가속기 아키텍처를 비교 분석하여 워크로드별 최적의 하드웨어 구조를 탐구합니다.

### 03. npu_prototyping
NPU의 핵심 유닛(MAC) 설계부터 통합 시뮬레이션 환경 구축까지의 과정을 다룹니다. Python과 Verilog의 교차 검증을 통해 하드웨어 모델의 정확성을 확보하고 Roofline 분석을 통한 설계 최적화를 수행합니다.

### 04. system_optimization
설계 공간 탐색(DSE)을 통해 최적의 파레토 프론트(Pareto Front)를 식별합니다. 자율주행, LLM 등 실제 응용 시나리오에 맞춘 하드웨어 전문화(Specialization) 및 가속기 최적화 전략을 다룹니다.

---

## 🏗️ Directory Structure

```text
npu-aware-engineering/
├── README.md
├── 00_docs/
├── 01_system_foundations/
├── 02_accelerator_architecture/
├── 03_npu_prototyping/
└── 04_system_optimization/
```
---
## ⚖️ License & Copyright
This project is licensed under the terms of the **MIT License**.
Copyright © 2026 Ogi. All rights reserved.
<br>
*연구 목적의 참조는 환영하며, 인용 시 출처를 밝혀주시기 바랍니다.*