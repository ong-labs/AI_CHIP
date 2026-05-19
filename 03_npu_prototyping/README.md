# 03_npu_prototyping: NPU Specifications & Hardware Prototyping

이 폴더는 추상적인 아키텍처 분석 단계를 넘어, 독자적인 도메인 특화 가속기(DSA)인 `edu-NPU-v1`의 하드웨어 스펙을 명세하고 실제 연산기 및 메모리 서브시스템의 물리적 비용을 모델링하는 **NPU 프로토타이핑(Prototyping)** 단계를 다룹니다. 최상위 의사결정 파이프라인부터 최소 산술 유닛인 MAC(Multiply-Accumulate), 계층형 메모리 구조의 지연 시간과 에너지를 유기적으로 연결하여 하드웨어 설계의 기초를 완성합니다.

---

## 📂 저장소 워크플로우 (A-L-M)

본 저장소는 아키텍처 설계 및 프로토타이핑의 완성도를 보장하기 위해 엔지니어링 표준 사이클에 맞추어 유기적으로 연계되어 있습니다.

1. **analysis**: 하드웨어 설계 사양 정의, 의사결정 트리 흐름 및 산술 컴포넌트 동작의 이론적 비용 분석 보고서
2. **lab**: NPUConfig 명세 프레임워크와 MAC 및 3-Tier 메모리 모델을 파이썬 코드로 빌드하고 하드웨어 제원을 실측하는 실습 단계
3. **mastery**: 설계 변수의 수학적 정합성을 확인하고 최상위 아키텍처 프레임워크의 논리적 무결성을 검증하는 숙달 단계

---

## 📝 커리큘럼 로드맵

### Unit 1. NPU 아키텍처 사양 정의 및 설계 흐름 분석
NPU 설계의 출발점인 목표 워크로드 설정을 기반으로 데이터 타입 정밀도, PE 배열 구조, 데이터플로우를 결정하고 이론적 피크 TOPS 성능을 정량화하는 전체 설계 파이프라인과 의사결정 트리를 정립합니다.

* **[analysis]** [01_npu_architecture_report.md](./analysis/01_npu_architecture_report.md): 핵심 아키텍처 파라미터 정의 및 이론적 피크 TOPS 성능 정량 모델링 보고서
* **[analysis]** [01_block_diagram_scrutiny.md](./analysis/01_block_diagram_scrutiny.md): 워크로드 정의부터 성능 분석으로 이어지는 NPU 설계 의사결정 흐름 및 블록 다이어그램 분석 가이드
* **[lab]** [01_npu_architecture_bench.py](./lab/01_npu_architecture_bench.py): 구조체 기반 하드웨어 명세 관리 및 Peak TOPS 자동 산출 스펙 에스티메이터 실습 소스 코드
* **[mastery]** [01_npu_spec_assessment.md](./mastery/01_npu_spec_assessment.md): 아키텍처 사양 변수 및 설계 다이어그램 의사결정 논리 제원의 무결성을 최종 검증하는 개념 확인 문제집

### Unit 2. MAC 산술 컴포넌트 및 하드웨어 모델링
NPU의 가장 작은 계산 엔진이자 핵심 연산 블록인 MAC 유닛의 추상화 레벨별 하드웨어 모델링 기법을 학습하고, 정수형 연산 시의 누산기 비트 폭 확장 필요성 및 다중 계층 메모리 시스템의 전력/타이밍 지연 비용을 시뮬레이션합니다.

* **[analysis]** [02_mac_modeling_report.md](./analysis/02_mac_modeling_report.md): MAC 유닛의 데이터 타입별 설계 원리, 에너지 비용 프로필 및 정수형 누적 오버플로우 방지 구조 분석 보고서
* **[lab]** [02_hardware_comp_bench.py](./lab/02_hardware_comp_bench.py): 산술 유닛 오버플로우 기능 검증 및 Register-SRAM-DRAM 3단계 메모리 계층 지연 시간/에너지 비용 모델링 실습 소스 코드

---

## 🏗️ Directory Structure

```text
03_npu_prototyping/
├── README.md
├── analysis/
│   ├── 01_block_diagram_scrutiny.md      # 설계 의사결정 파이프라인 블록 다이어그램 분석
│   ├── 01_npu_architecture_report.md     # 핵심 아키텍처 제원 정의 및 피크 성능 분석 보고서
│   └── 02_mac_modeling_report.md         # MAC 산술 유닛 설계 및 추상화 레벨 모델링 보고서
├── lab/
│   ├── 01_npu_architecture_bench.py      # NPUConfig 명세 구조체 및 성능 에스티메이터 빌드
│   └── 02_hardware_comp_bench.py         # MAC 정합성 검증 및 3-tier 메모리 비용 모델 실습
└── mastery/
    └── 01_npu_spec_assessment.md         # 아키텍처 스펙 및 설계 플로우 논리 최종 숙달 검증
```

---

*본 저장소는 독자적인 가속기 하드웨어 시스템 통합을 목표로 하며, 명세된 모든 프로토타이핑 데이터의 정합성은 상호 검증되었습니다.*
