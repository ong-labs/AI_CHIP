# 06_npu_mathemactical.md: NPU Simulator Measurement Metrics Mathematical Modeling and Formula Analysis Report

본 보고서는 통합 가속기 시뮬레이터 엔진의 소스 코드 내부에 설계된 하드웨어 비용 계측용 수학적 모델링 공식들을 정량적으로 분석하기 위해 작성되었습니다. `npu.run(A, B)` 아키텍처 호출 시 수집되는 6가지 출력 계약(Contract) 지표의 산술 메커니즘을 컴퓨터 구조학적 관점에서 해체하고, 아키텍처 가변 변수가 전체 가속 시스템 전성비 및 지연 시간에 미치는 영향력을 정밀 고찰합니다.

---

## 1. 결과 행렬 및 수치적 정합성 (`C` - Functional Correctness)

### 1.1 누산 정밀도(Accumulator Precision) 모사 계산식
시뮬레이터 백엔드는 하드웨어 내부에서 Mixed-Precision 연산 시 발생하는 데이터 타입 캐스팅 및 비트 확장 마진을 실제 NumPy 연산 레벨에서 정밀하게 모사합니다.

```python
accum_np = {
    "int8": np.int32,
    "int16": np.int32,
    "fp16": np.float32,
    "bf16": np.float32,
    "fp32": np.float32,
}[config.dtype]

C = A.astype(accum_np) @ B.astype(accum_np)
```

### 1.2 수학적 표현식

출력 행렬 $C \in \mathbb{R}^{M \times N}$의 각 개별 원소 $C_{ij}$는 입력 행렬 $A \in \mathbb{R}^{M \times K}$와 가중치 행렬 $B \in \mathbb{R}^{K \times N}$ 간의 내적 연산으로 완결되며 다음과 같이 정의됩니다.

$$C = A \times B$$

$$C_{ij} = \sum_{k=1}^{K} A_{ik} B_{kj}$$

### 1.3 아키텍처적 공학 의미

* **하드웨어 에뮬레이션 정합성**: 단순히 속도만 예측하는 성능 모델러를 넘어 실제 행렬 곱셈을 물리 데이터 레벨에서 직접 수행하여 알고리즘 무결성을 증명하는 백엔드 축입니다.
* **검증 골든 레퍼런스 수립**: 반환된 $C$ 행렬은 `np.allclose()` 검증 함수를 통과하여 실제 하드웨어 RTL 출력과의 데이터 정합성을 크로스체크하는 수치적 기준점이 됩니다.

---

## 2. 총 실행 시간 모델링 (`cycles` - Total Execution Latency)

가속기의 총 가동 주기는 하드웨어 병렬 연산 주기, 오프칩 전송 주기, 호스트 명령 가동 오버헤드의 상호 관계식으로 산출됩니다. 가상 가속 평면의 행 크기($PE_R$)와 열 크기($PE_C$) 사양을 기준으로 타일 파티셔닝을 선행 선언합니다.

### 2.1 축별 2차원 매핑 타일(Tile) 분출 공식

$$nt_m = \left\lceil \frac{M}{PE_R} \right\rceil, \quad nt_n = \left\lceil \frac{N}{PE_C} \right\rceil, \quad nt_k = \left\lceil \frac{K}{PE_R} \right\rceil$$

### 2.2 순수 연산 사이클 공식 (`compute_cycles`)

가중치 고정(Weight-Stationary) 중첩 루프 하에서 단일 타일 블록당 소모되는 클럭 박자는 $cycles\_per\_tile = PE_R$로 수렴합니다. 시스톨릭 파이프라인의 물리 구조적 지연 특성인 초기 데이터 진입(Fill) 및 잔여 데이터 하차(Drain) 타이밍 오버헤드가 가산되어 전역 연산 사이클이 완성됩니다.

$$compute\_cycles = nt_m \cdot nt_n \cdot nt_k \cdot PE_R + (PE_R + PE_C - 1)$$

### 2.3 외부 메모리 대역폭 전송 사이클 공식 (`dram_cycles`)

시스템 설정 주파수($clock_{GHz}$)와 외장 버스 대역폭 제원($dram\_bw_{GB/s}$)을 기반으로 단일 클럭 사이클당 통과 가능한 최대 데이터 바이트 용량을 도출한 뒤, 전역 데이터양을 나누어 올림 처리합니다.

$$bytes\_per\_cycle = \frac{dram\_bw_{GB/s}}{clock_{GHz}}$$

$$dram\_cycles = \left\lceil \frac{dram\_total\_bytes}{bytes\_per\_cycle} \right\rceil$$

### 2.4 전역 통합 사이클 공식 (`total_cycles`)

$$total\_cycles = \max(compute\_cycles,\ dram\_cycles) + overhead\_cycles$$

$$overhead\_cycles = clock_{GHz} \times 1000 \quad (\approx 1\,\mu\text{s 호스트 디스패치 오버헤드 고정 가산})$$

* **공학적 의의**: 하드웨어 가속기 레벨에서 동작하는 더블 버퍼링(Double Buffering) 구조 하의 숨겨진 타임 패널티를 모사하기 위해 연산과 전송 중 가장 가혹한 병목 자원 하나만이 전체 지연 시간을 지배한다는 Roofline 아키텍처 사고를 그대로 정량화하여 투영한 공식입니다.

---

## 3. 메모리 입력 대역폭 계측 (`dram_read_bytes` - Off-chip Read Traffic)

가중치 고정 데이터플로우 제어 특성에 따른 SRAM 버퍼 가용 용량 임계 마진 돌파 여부를 추적 집계하는 공식입니다.

### 3.1 원자 단위 서브 타일 물리 바이트 폭 선언

$$weight\_tile\_bytes = PE_R \times PE_C \times bytes_e$$

$$input\_tile\_bytes = PE_R \times PE_R \times bytes_e$$

### 3.2 전역 레이어별 총 요구 차원 제원 용량

$$weight\_full\_bytes = nt_n \times nt_k \times weight\_tile\_bytes$$

$$input\_full\_bytes = nt_m \times nt_k \times input\_tile\_bytes$$

### 3.3 온칩 SRAM 가용 용량 한계선에 따른 이진 필터링 분기 공식

* **가중치 메모리 적재 트래픽 (`weight_dram`)**:
* **SRAM 용량 넉넉함 ($weight\_full\_bytes \le SRAM_{bytes}$)**: 최초 1회 전체 적재 후 내부 상주 재사용

$$weight\_dram = weight\_full\_bytes$$


* **SRAM 용량 부족함 ($weight\_full\_bytes > SRAM_{bytes}$)**: $M$축 타일 루프가 전개될 때마다 외부 대역으로부터 원본 데이터를 가혹하게 반복 재로드

$$weight\_dram = nt_m \times weight\_full\_bytes$$




* **피처 맵 입력 메모리 적재 트래픽 (`input_dram`)**:
* **SRAM 마진 충분함 ($input\_full\_bytes \le SRAM_{bytes} - \min(weight\_full\_bytes, SRAM_{bytes})$)**: 온칩 내에 전체를 버퍼링하여 트래픽 억제

$$input\_dram = input\_full\_bytes$$


* **SRAM 마진 부족함 (용량 임계점 돌파 패널티)**: $N$축 타일 스케일 가변 루프 박자마다 외장 대역으로부터 통째로 반복 리드

$$input\_dram = nt_n \times input\_full\_bytes$$





### 3.4 최종 DRAM Read 트래픽 마감 공식

$$dram\_read\_bytes = weight\_dram + input\_dram$$

---

## 4. 메모리 출력 대역폭 계측 (`dram_write_bytes` - Off-chip Write Traffic)

### 4.1 출력 원자 단위 타일 바이트 폭 선언

$$output\_tile\_bytes = PE_R \times PE_C \times bytes_e$$

### 4.2 전역 Output Write 트래픽 누적 공식

모든 내부 $K$축 차원의 부분합 누산 연산이 완벽히 종결된 클럭 타이밍 기점에서 완성형 타일 데이터를 오프칩 대역으로 내보내는 물리 흐름입니다.

$$dram\_write_bytes = nt_m \times nt_n \times output\_tile\_bytes$$

---

## 5. 공간 자원 가동 활용 효율성 (`pe_utilization` - Hardware Efficiency)

하드웨어가 물리적으로 가질 수 있는 이론적 피크 연산 가용 한계 공간과 실제 행렬식의 원소 계산을 위해 유효하게 일한 횟수 간의 비율입니다.

### 5.1 실제 유효 연산량 (`actual_macs`)

$$actual\_macs = M \cdot N \cdot K$$

### 5.2 하드웨어 평면 연산량 한계 총합 (`full_pe_macs`)

여기서 마지막 항 $PE_R$은 하드웨어 가속기 구조상 $K$축 연산 처리를 위해 매 사이클마다 스트리밍 투입되는 물리적 하드웨어 비트 길이선 폭을 정의합니다.

$$full\_pe\_macs = nt_m \cdot nt_n \cdot nt_k \cdot PE_R \cdot PE_C \cdot PE_R$$

### 5.3 공간 활용 효율 수식 선언

$$pe\_utilization = \frac{actual\_macs}{full\_pe\_macs}$$

* **공학적 의의**: 대규모 연산 어레이($64 \times 64$ 등)를 구비했더라도 인가된 워크로드의 스케일 차원이 평면보다 작으면 칩 평면의 가장자리 유닛들이 빈 값을 채우는 제로 패딩 에지 타일 패널티(`edge tile padding`) 처리에 대거 동원되므로 utilization 수치가 급감하여 구조적 자원 낭비 상태임을 정량적으로 가리킵니다.

---

## 6. 총 전력 프로필 물리 비용 (`energy_pj` - Energy Infrastructure)

하드웨어 내부 연산 코어와 온칩/오프칩 다중 메모리 서브시스템 계층 전체의 물리 소비 에너지를 피코줄($\text{pJ}$) 단위로 수집 합산합니다.

### 6.1 에너지 소스 파트별 연산 공식

* **산술 코어 소모 에너지**: 유효 총 MAC 연산 회수에 입력 사양별 물리 전하 이동 pJ 스케일링 가중치를 곱해 정량 계산합니다.

$$mac\_energy = actual\_macs \times mac\_energy_{pJ}$$


* **오프칩 메모리 트래픽 소모 에너지**: 총 DRAM 입출력 바이트 총합선에 off-chip 패키지 배선 전하 제어 패널티 가중치를 가산합니다.

$$dram\_energy = dram\_total\_bytes \times dram\_energy_{pJ/byte}$$


* **온칩 버퍼 메모리 소모 에너지**: 모든 DRAM 바이트는 최소 1회 이상 온칩 SRAM 레벨을 관통 횡단하므로 코드 사양 구조에 의거하여 $sram\_accesses = dram\_total\_bytes$ 관계가 성립합니다.

$$sram\_energy = sram\_accesses \times sram\_energy_{pJ/byte}$$



### 6.2 전역 토탈 에너지 통합 수식

$$energy_{pj} = mac\_energy + dram\_energy + sram\_energy$$

---

## 7. 가속기 성능 계측 지표 종합 요약표 (Comprehensive Metric Matrix)

시뮬레이터의 최종 출력값을 한눈에 가시적으로 스캔하기 위한 전역 핵심 계산 매트릭스 아카이브입니다.

| 출력 식별자 | 아키텍처적 핵심 유효 계산 수식 | 공학적 추정 기법의 본질 |
| --- | --- | --- |
| **`C`** | $A \times B \quad \left(C_{ij} = \sum A_{ik} B_{kj}\right)$ | NumPy 백엔드를 통한 수치적 실제 계산 및 정합성 방어 |
| **`cycles`** | $\max(compute\_cycles,\ dram\_cycles) + overhead$ | 루프 스케줄링 이론에 기반한 지연/통신 타임 버퍼 오버랩 추정 |
| **`dram_read_bytes`** | $weight\_dram + input\_dram$ | SRAM 용량 한계점 극복 여부에 따른 바이너리 재로딩 트래픽 실측 |
| **`dram_write_bytes`** | $nt_m \times nt_n \times output\_tile\_bytes$ | 내적 연산 최종 마감 기점의 데이터 오프칩 하차량 정량 계산 |
| **`pe_utilization`** | $actual\_macs / full\_pe\_macs$ | 하드웨어 최대 계산량 한계 공간 대비 유효 연산 가동 공간 효율화율 |
| **`energy_pj`** | $mac\_energy + dram\_energy + sram\_energy$ | 산술 코어 및 3-Tier 다중 계층 메모리 전하 비용 물리 전폭 합산 |

---

## 💡 결론 및 요약 (Conclusion)

본 과제에서 명세화한 가속기 계측 수식 모델러는 임의의 정방형/비정방형 가상 인공지능 행렬곱 알고리즘 자극 세트가 인가되었을 때, 타겟 가속기의 물리 사양 구성 조건에 맞추어 "성능과 에너지의 상호 인과관계를 단 한 번의 고속 해석적 계산 루프로 정량 산출해 내는 정밀한 수학적 성능 에스티메이터"입니다.

이 모델링 공식들을 디딤돌로 삼아 차후 전개될 대단원인 시스템 최적화 주차에서 수백 개의 아키텍처 파라미터 조합을 초고속 다차원 스윕하여 경쟁력 있는 파레토 설계 해 집합(Pareto Front)을 완벽히 식별해 내는 하드웨어-소프트웨어 Co-design 최적화의 핵심 수학적 나침반으로 기능하게 됩니다.
