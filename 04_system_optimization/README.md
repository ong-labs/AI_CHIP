# 04_system_optimization: Hardware-Software Co-Design & System Optimization

이 폴더는 기초적인 NPU 프로토타이핑 단계를 넘어, 하드웨어 아키텍처와 소프트웨어 워크로드의 접점을 정밀하게 제어하는 **하드웨어-소프트웨어 공동 설계(HW-SW Co-Design)** 및 시스템 전성비 최적화를 다룹니다. 다차원 아키텍처 하이퍼파라미터 조합을 스윕하여 최적의 파레토 프론트(Pareto Front)를 도출하는 디자인 공간 탐색(DSE)부터, 고주파 구동을 위한 파이프라인 RTL 고도화, 그리고 2차원 시스톨릭 어레이(Systolic Array) 배선 토폴로지 장악을 통해 최상위 시스템 최적화 인프라를 완수합니다.

---

## 📂 저장소 워크플로우 (A-L-M)

본 저장소는 아키텍처 설계와 시스템 최적화의 완성도를 공학적으로 보장하기 위해 엔지니어링 표준 사이클에 맞추어 유기적으로 연계되어 있습니다.

1. **analysis**: 디자인 공간 탐색 파레토 최적화 수식 유도, 양산형 MAC 파이프라인 분리 및 시스톨릭 어레이 기하학 배선 토폴로지의 이론적 비용 분석 보고서
2. **lab**: 다차원 아키텍처 변수 자동 탐색 스크립트와 포화 연산 기반 MAC 코어 및 2차원 시스톨릭 가속 패브릭을 Verilog로 빌드하고 검증하는 실습 단계
3. **mastery**: 최적화 변수의 수학적 트레이드오프 정합성을 확인하고 최상위 아키텍처 오케스트레이션 프레임워크의 구조적 무결성을 최종 검증하는 숙달 단계

---

## 📝 커리큘럼 로드맵

### Unit 1. 디자인 공간 탐색(DSE) 및 파레토 최적화 기법
NPU 하드웨어 제원 사양(SRAM 용량, 연산기 배열 형상, 동작 주파수, 메모리 대역폭) 가변에 따른 하드웨어 비용의 비선형적 변동 추이를 추적하고, 거시적 보틀넥 진단을 통해 최적의 면적 대비 성능 효율을 갖는 파레토 프론트 해 집합을 추출합니다.

* **[analysis]** [01_npu_dse_report.md](./analysis/01_npu_dse_report.md): 하드웨어 아키텍처 변수 스윕 가동 및 전성비 파레토 프론트 최적화 분석 보고서
* **[lab]** [01_npu_dse_bench.py](./lab/01_npu_dse_bench.py): 다차원 디자인 공간 탐색(Design Space Exploration) 및 파레토 최적 해 집합 자동 추출 실습 소스 코드
* **[lab]** [results/01_pareto_front.png](./lab/results/01_pareto_front.png): 디자인 공간 탐색(DSE) 아키텍처 변수 스윕을 통해 도출된 면적 비용 대비 전성비 최적의 파레토 프론트 플롯 그래프

### Unit 2. 고속 가속기 시스템을 위한 양산형 MAC RTL 아키텍처 분석
실제 반도체 제조 공정 및 FPGA 환경에서 안정적인 타이밍 클로저(Timing Closure)를 달성하기 위해 곱셈과 가산 회로 사이에 레지스터 장벽을 세우는 2단계 파이프라인 구조를 안착시키고, 데이터 파괴를 방지하는 포화 연산(Saturation) 회로의 무결성을 검증합니다.

* **[analysis]** [02_prod_mac_rtl_report.md](./analysis/02_prod_mac_rtl_report.md): 고속 가속기 시스템을 위한 파이프라인 및 포화 연산 기반 양산형 MAC RTL 구조 분석 보고서
* **[analysis]** [02_systolic_methodology.md](./analysis/02_systolic_methodology.md): Two-Pass 기법 및 Seven-Step 패턴 기반 시스톨릭 어레이 RTL 분석 방법론 보고서
* **[lab]** [02_prod_mac/](./lab/02_prod_mac/): 가변 파라미터, 글로벌 인에이블(`en`), 국소 클리어 및 Sticky overflow 경고 비트가 내장된 `mac_v2.v` 코어 및 cocotb 테스트벤치 실습 폴더

### Unit 3. Two-Pass 기법 및 구조적 배선 토폴로지 기반 시스톨릭 어레이 분석
수만 라인에 달하는 대규모 가속기 하드웨어 IP 분석 시 인지 부하를 차단하는 Two-Pass(Top-down & Bottom-up) 구조적 분석 기법과 Seven-Step 파일 해체 패턴을 정립하고, 2차원 공간 상에 가로축 액티베이션 시프트망과 세로축 부분합 누산 체인을 형성하는 물리 배선 패브릭을 해체합니다.

* **[analysis]** [03_systolic_array_grid_interconnect_report.md](./analysis/03_systolic_array_grid_interconnect_report.md): 2차원 Generate 그리드 및 가상 와이어 토폴로지 기반 시스톨릭 어레이 배선 아키텍처 분석 보고서
* **[lab]** [03_systolic_array/](./lab/03_systolic_array/): 대규모 플랫 벡터 버스(Flat Vector Bus) 제어 기반 `pe_array.v` 모듈, 입력 계단식 지연 셔플러(`input_skew.v`), 가중치 브로드캐스트 분배기(`weight_loader.v`), 결과 버퍼 수집기(`output_collect.v`) 및 `systolic_top.v` 통합 와이어 조립 코시뮬레이션 실습 폴더

### Unit 4. 배치 스케일링 제어 및 다차원 성능 축(Performance Axes) 분석
배치 크기(Batch Size) 가변에 따른 하드웨어 처리 지연 시간(Latency)과 시스템 처리량(Throughput, QPS) 간의 엔지니어링 트레이드오프 곡선을 도출하고, 다차원 면적 비용 모델을 결합하여 무조건적인 자원 확장 대비 실질 성능 이득을 정량 평가합니다.

* **[lab]** [04_perf_axes.py](./lab/04_perf_axes.py): 배치 크기별 지연시간/처리량 변동 곡선 및 다차원 면적 비용 모델 분석 실습 소스 코드
* **[lab]** [results/03_batching_curve.png](./lab/results/03_batching_curve.png): 배치 크기 가변에 따른 지연시간 및 QPS 성능 변동 특성 실측 가시화 플롯 그래프

### Unit 5. 도메인 특화 핵심 어플리케이션 워크로드 프로파일링
실제 산업계에서 널리 활용되는 자율주행(Perception), 대규모 언어 모델(LLM Prefill/Decode), 영상처리 엣지 등 3대 핵심 시나리오 워크로드를 가상 NPU 상에 인가하여 프레임 레이턴시, TOPS 및 전성비를 다각도로 실측 프로파일링합니다.

* **[lab]** [05_app_workload.py](./lab/05_app_workload.py): 자율주행·LLM 챗봇·영상처리 등 3대 주요 어플리케이션 워크로드 가동 및 성능 지표 측정 실습 소스 코드

### Unit 6. 도메인 특화 아키텍처 시나리오 튜닝 및 성능 회귀 분석
특정 대상 어플리케이션(LLM 챗봇)의 전성비와 처리량 목표 달성을 위해 하드웨어 제원(PE, SRAM 등)을 집중 최적화 가변하는 시나리오 튜닝을 수행하고, 이 아키텍처적 변동이 타 어플리케이션 도메인에 미치는 성능 저하(Regression) 및 다이 면적 증가 비용을 종합 진단합니다.

* **[lab]** [06_scenario_tuning.py](./lab/06_scenario_tuning.py): 특정 시나리오(LLM) 최적화 아키텍처 튜닝 및 전역 도메인 성능 회귀 분석 실습 소스 코드
* **[lab]** [results/05_scenario_tuning.png](./lab/results/05_scenario_tuning.png): 아키텍처 튜닝 적용 전/후 주요 어플리케이션별 타겟 우선순위 메트릭 변동 추이 비교 바 차트

---

## 🏗️ Directory Structure

```text
04_system_optimization/
├── README.md
├── analysis/
│   ├── 01_npu_dse_report.md              # 하드웨어 아키텍처 변수 스윕 및 파레토 프론트 최적화 보고서
│   ├── 02_prod_mac_rtl_report.md         # 파이프라인 및 포화 연산 기반 양산형 MAC RTL 구조 분석 보고서
│   ├── 02_systolic_methodology.md        # Two-Pass 기법 및 Seven-Step 패턴 기반 분석 방법론 보고서
│   └── 03_systolic_array_grid.md         # 2차원 Generate 그리드 및 가상 와이어 토폴로지 배선 보고서
├── lab/
│   ├── 02_prod_mac/
│   │   ├── mac_prod.v                    # 2-stage 파이프라인, 포화 연산 및 글로벌 인에이블 탑재 MAC RTL
│   │   ├── Makefile                      # 코시뮬레이션 컴파일 및 자동화 빌드 스크립트
│   │   ├── surfer.cmd                    # 시뮬레이션 결과 파형 디버깅을 위한 Surfer 신호 자동 로드 스크립트
│   │   └── test_mac_prod.py              # Sticky overflow 및 파이프라인 레이턴시 검증 테스트벤치
│   └── 03_systolic_array/
│   │   ├── cocotb_helpers.py             # 테스트벤치 구동 및 수치 팩킹을 위한 공통 cocotb 헬퍼 함수 스크립트
│   │   ├── input_skew.v                  # 시스톨릭 웨이브 정렬을 위한 행별 계단식 지연 셔플러 버퍼
│   │   ├── Makefile                      # 시스톨릭 전체 시스템 통합 테스트 빌드 스크립트
│   │   ├── output_collect.v              # 최하단 부분합 버스트 캡처 및 유효성 추적 레지스터 모듈
│   │   ├── pe_array.v                    # ROWS × COLS 프로세싱 엘리먼트 2차원 그리드 평면 배선 모듈
│   │   ├── surfer.cmd                    # 시스톨릭 어레이 파형 디버깅을 위한 Surfer 신호 자동 로드 스크립트
│   │   ├── systolic_top.v                # 가중치 로더, 인풋 스큐, PE 어레이, 아웃풋 수집기 통합 오케스트레이터
│   │   ├── test_input_skew.py            # 입력 스큐 모듈의 계단형 지연 및 정렬 기능 검증 테스트벤치
│   │   ├── test_output_collect.py        # 출력 수집 모듈의 부분합 캡처 및 유효성 파이프라인 검증 테스트벤치
│   │   ├── test_pe_array.py              # 4-Corner PE 검증 및 NumPy 크로스체킹 통합 테스트벤치
│   │   ├── test_systolic_top.py          # 5대 서브모듈 통합 시스템에 대한 End-to-End 정합성 검증 테스트벤치
│   │   ├── test_weight_loader.py         # 가중치 로더 모듈의 1클럭 브로드캐스트 동작 검증 테스트벤치
│   │   └── weight_loader.v               # 가중치 고정(WS) 구동을 위한 1클럭 브로드캐스트 분배 시퀀서
│   └── results/
│   │   ├── 01_pareto_front.png           # 디자인 공간 탐색(DSE)을 통해 도출된 사양별 최적의 전성비 파레토 프론트 플롯 그래프
│   │   ├── 04_batching_curve.png         # 배치 크기 가변에 따른 시스템 지연시간(Latency) 및 처리량(Throughput) 변동 곡선 그래프
│   │   └── 06_scenario_tuning.png        # LLM 시나리오 최적화 아키텍처 튜닝 적용 전/후 주요 앱별 성능 메트릭 비교 바 차트
│   ├── 01_npu_dse_bench.py               # 다차원 디자인 공간 탐색 및 파레토 프론트 추출 스크립트
│   ├── 04_perf_axes.py                   # 배치 크기별 지연시간/처리량 변동 곡선 및 다차원 비용 모델 분석 스크립트
│   ├── 05_app_workload.py                # 자율주행·LLM 챗봇·영상처리 등 3대 주요 어플리케이션 워크로드 측정 스크립트
│   └── 06_scenario_tuning.py             # 특정 시나리오(LLM) 최적화 아키텍처 튜닝 및 성능 회귀 분석 스크립트
└── mastery/
    └── 01_dse_pareto_assessment.md       # 디자인 공간 탐색 알고리즘 및 비용 트레이드오프 숙달 문제집
```

---

*본 저장소는 독자적인 가속기 하드웨어 고속 시스템 조립 및 최적화를 목표로 하며, 명세된 모든 시스템 파라미터와 배선 토폴로지의 물리적 정합성은 상호 검증되었습니다.*
