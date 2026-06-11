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

### Unit 3. Verilog HDL 기반 MAC RTL 설계 및 하드웨어-소프트웨어 공동 검증
인공지능 가속기의 핵심 연산 블록인 MAC 유닛을 Verilog HDL 코드로 구현하고, 파이썬 기반 cocotb 프레임워크와 Surfer 파형 뷰어를 결합하여 매 사이클 단위로 하드웨어-소프트웨어 통합 정합성을 실측 디버깅합니다.

* **[analysis]** [03_npu_mac_rtl_report.md](./analysis/03_npu_mac_rtl_report.md): Verilog MAC의 마이크로아키텍처 구조 분석, 넌블로킹 할당문 및 사이클 트레이싱 분석 보고서
* **[lab]** [03_mac_verilog/](./lab/03_mac_verilog/): cocotb 및 Icarus Verilog 기반의 하드웨어 MAC 유닛 컴파일, 파이썬 자극 인가 및 Surfer 파형 추출 통합 실습 폴더
* **[mastery]** [03_mac_verification.md](./mastery/03_mac_verification.md): cocotb 코시뮬레이션 스케줄링 이론, 부호 있는 연산 규칙 및 검증 아키텍처 무결성을 평가하는 20문항의 숙달 퀴즈집

### Unit 4. 정적 컴포넌트 결합 및 통합 NPU 시뮬레이터 오케스트레이션
설정(Config), 컴포넌트(Memory, MAC), 계산 토폴로지(Systolic Array) 자산을 결합하여 가상 시간 축을 부여하고 실행 순서를 제어하는 가속기 커맨드 프로세서 오케스트레이션 레이어를 구축합니다.

* **[analysis]** [04_npu_intergration_report.md](./analysis/04_npu_intergration_report.md): 정적 컴포넌트 결합을 통한 실행 및 측정 가능한 통합 NPU 시뮬레이터 설계 보고서
* **[lab]** [04_npu_simulator_bench.py](./lab/04_npu_simulator_bench.py): 중첩 타일 루프 스케줄링 이론 기반의 weight-stationary 가상 NPU 실행 엔진 실습 소스 코드
* **[mastery]** [04_npu_integration.md](./mastery/04_npu_integration.md): 통합 시뮬레이터 모델링 기법, 타일 분할 원리 및 하드웨어 활용 효율 검증 문제집

### Unit 5. 하이브리드 Analytical 시뮬레이터 개념 및 Roofline 성능 분석
실제 결과 행렬은 NumPy 소프트웨어로 연산하되 물리 비용 성능 지표는 수식으로 고속 추정하는 하이브리드 검증 구조를 이해하고, 다양한 워크로드에 대한 Roofline bound와 비교 분석을 수행합니다.

* **[analysis]** [05_analytical_npu_simulator.md](./analysis/05_analytical_npu_simulator.md): 하이브리드 검증 기법 기반의 Analytical NPU 시뮬레이터 개념 및 아키텍처 분석 보고서
* **[lab]** [05_npu_roofline_bench.py](./lab/05_npu_roofline_bench.py): 5대 신경망 워크로드 인가 및 타사 상용 가속기 칩셋들과의 Roofline 한계 초과 교차 벤치마크 실습 소스 코드
* **[lab]** [results/05_npu_roofline.png](./lab/results/05_npu_roofline.png): 타사 칩셋 대비 독자 NPU 사양의 워크로드별 지연시간 병목 구간 실측 가시화 플롯 그래프
* **[mastery]** [05_mac_rtl_design.md](./mastery/05_mac_rtl_design.md): 순차 논리 회로 체계, 넌블로킹 할당문 동작 이론 및 동기식 리셋 검증 숙달 문제집

### Unit 6. 시뮬레이터 계측 지표 수학적 모델링 및 하드웨어 트레이드오프 분석
시뮬레이터가 반환하는 6대 핵심 출력 지표의 수학적 유도 수식을 정량 분석하고, 하드웨어 사양 변경(SRAM 확장, PE 비대화 등)이 유발하는 물리적 트레이드오프와 Bottleneck의 인과관계를 진단합니다.

* **[analysis]** [06_npu_mathemactical.md](./analysis/06_npu_mathemactical.md): NPU 시뮬레이터 계측 지표 수학적 모델링 및 계산식 분석 보고서
* **[lab]** [06_tradeoff_bench.py](./lab/06_npu_tradeoff_bench.py): 특정 하드웨어 스펙 보틀넥 진단 후 단일 사양 최적화 변경에 따른 Before/After 정량 비교 실습 소스 코드

### Unit 7. Production-Ready 양산형 가속기 MAC RTL 설계 및 파이프라인 검증
실제 반도체 칩 환경 사양에 맞추어 가변 정밀도 파라미터화, Active-low 리셋, 글로벌 Enable, 포화 연산(Saturation) 및 주파수 한계 돌파를 위한 2단계 하드웨어 파이프라인 고도화를 수행합니다.

* **[analysis]** [07_npu_mac_v2_report.md](./analysis/07_npu_mac_v2_report.md): Production-Ready 양산형 가속기 MAC RTL 설계 및 파이프라인 검증 보고서
* **[lab]** [07_ad_mac/](./lab/07_ad_mac/): 고주파 구동용 파이프라인 분리형 `mac_v2.v` 모듈, cocotb 기반 6종 정밀 코시뮬레이션 검증 툴체인 아카이브

---

## 🏗️ Directory Structure

```text
03_npu_prototyping/
├── README.md
├── analysis/
│   ├── 01_block_diagram_scrutiny.md      # 설계 의사결정 파이프라인 블록 다이어그램 분석 가이드
│   ├── 01_npu_architecture_report.md     # 핵심 아키텍처 제원 정의 및 피크 성능 분석 보고서
│   ├── 02_mac_modeling_report.md         # MAC 산술 유닛 설계 및 추상화 레벨 모델링 보고서
│   ├── 03_npu_mac_rtl_report.md          # Verilog MAC 회로 마이크로아키텍처 구조 및 시뮬레이션 분석 보고서
│   ├── 04_npu_intergration_report.md     # 정적 컴포넌트 결합을 통한 실행 및 측정 가능한 통합 시뮬레이터 설계 보고서
│   ├── 05_analytical_npu_simulator.md    # 하이브리드 검증 기법 기반의 Analytical NPU 시뮬레이터 개념 분석 보고서
│   ├── 06_npu_mathemactical.md           # NPU 시뮬레이터 계측 지표 수학적 모델링 및 계산식 분석 보고서
│   └── 07_npu_mac_v2_report.md           # Production-Ready 양산형 가속기 MAC RTL 설계 및 검증 보고서
├── lab/
│   ├── 03_mac_verilog/
│   │   ├── mac.v                         # 부호 있는 INT8 곱셈 및 INT32 누적 기능을 갖춘 동기식 MAC RTL 설계도
│   │   ├── Makefile                      # Icarus Verilog 컴파일러 및 cocotb 테스트벤치 자동화 구동 스크립트
│   │   ├── surfer.cmd                    # 시뮬레이션 종료 후 Surfer 뷰어에 내부 신호선을 자동으로 프리로드하는 명령 파일
│   │   └── test_mac.py                   # 무작위 벡터 크로스체크 및 오버플로우 한계 돌파를 검증하는 cocotb 테스트벤치
│   ├── 07_ad_mac/
│   │   ├── mac_v2.v                      # 가변 파라미터, 클럭 게이팅, 포화 연산이 내장된 2-stage 파이프라인 MAC RTL
│   │   ├── Makefile                      # 양산형 코어 전용 Icarus Verilog 및 cocotb 실행 스크립트
│   │   ├── surfer.cmd                    # mac_v2.v 내부 신호선 디버깅을 위한 Surfer 자동 로드 프리셋 스크립트
│   │   └── test_mac_v2.py                # 포화 회로 및 유효성 시프트 6종 시나리오 검증 cocotb 테스트벤치
│   ├── results
│   │   └── 05_npu_roofline.png           # 타사 상용 가속기 대비 독자 NPU의 워크로드별 지연시간 실측 플롯
│   ├── 01_npu_architecture_bench.py      # NPUConfig 명세 구조체 및 성능 에스티메이터 빌드
│   ├── 02_hardware_comp_bench.py         # MAC 정합성 검증 및 3-tier 메모리 비용 모델 실습
│   ├── 04_npu_simulator_bench.py         # 중첩 타일 루프 스케줄링 기반 통합 NPU 시뮬레이터 엔진 실습
│   ├── 05_npu_roofline_bench.py          # 5대 워크로드 대상 타사 칩셋과의 Roofline 크로스 오버 벤치마크 실습
│   └── 06_npu_tradeoff_bench.py          # 보틀넥 아키텍처 자동 진단 및 사양 최적화 가변 실측 벤치마크 실습
└── mastery/
    ├── 01_npu_spec_assessment.md         # 아키텍처 스펙 및 설계 플로우 논리 최종 숙달 검증 문제집
    ├── 03_mac_verification.md            # cocotb 프레임워크 원리 및 하드웨어-소프트웨어 공동 검증 숙달 문제집
    ├── 04_npu_integration.md             # 통합 시뮬레이터 모델링 기법, 타일 분할 원리 및 활용 효율 검증 문제집
    └── 05_mac_rtl_design.md              # 순차 논리 회로 체계, 넌블로킹 할당문 동작 이론 숙달 문제집

```

---

*본 저장소는 독자적인 가속기 하드웨어 시스템 통합을 목표로 하며, 명세된 모든 프로토타이핑 데이터의 정합성은 상호 검증되었습니다.*
