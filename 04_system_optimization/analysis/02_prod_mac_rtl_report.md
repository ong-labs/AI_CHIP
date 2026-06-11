# 02_prod_mac_rtl_report.md: Mass-Production MAC RTL Architecture Analysis Report Based on Pipeline and Saturation Arithmetic for High-Speed Accelerator Systems

본 보고서는 실제 ASIC 및 FPGA 실리콘 제조 환경에서 안정적인 타이밍 클로저(Timing Closure)를 달성하고 연산 정합성을 보장할 수 있도록 설계 고도화를 이뤄낸 **`mac_v2.v`** 코드를 분석하기 위해 작성되었습니다. 기존의 개념 실증용 단일 스테이지 유닛(`mac.v`)이 가졌던 주파수 한계와 데이터 파괴 버그를 해소하기 위해 도입된 8대 마이크로아키텍처 개선 사항을 공학적으로 해체하여 리포팅합니다.

---

## 1. 하드웨어 스펙 비교 분석 (`mac.v` vs `mac_v2.v`)

양산형 하드웨어 IP 가 되기 위해 설계 레벨에서 변경된 핵심 아키텍처 제원 평면 비교입니다.

| 평가 항목 축 | 기초형 가속기 유닛 (`mac.v`) | 고도화 양산형 코어 (`mac_v2.v`) | 하드웨어 공학적 의의 및 기대 마진 |
| :--- | :--- | :--- | :--- |
| **파이프라인 구조** | 단일 스테이지 (1-Stage) | **2단계 파이프라인 (2-Stage)** | 조합회로 패스 분리를 통한 동작 주파수($F_{max}$) 대폭 상승 |
| **리셋 메커니즘** | Active-High 동기식 리셋 | **Active-Low 비동기식 리셋** | 산업 표준 규격 준수 및 초기 전원 인가 글리치 노이즈 방어 |
| **스펙 재사용성** | 고정형 사양 (INT8 / INT32) | **파라미터화 (Configurable)** | 가변 정밀도(INT4, INT8, INT16 등) 아키텍처 지원 |
| **예외 처리** | 사일런트 랩어라운드 발생 | **포화 연산 제어 (Saturation)** | 최대/최소 한계값 고정으로 데이터 가속 파괴 방지 |
| **인터페이스 흐름** | 핸드셰이크 프로토콜 부재 | **유효 신호 동기 파이프라인** | 외부 모듈 및 제어 버스와의 유기적 흐름 제어(Flow Control) |
| **가동 제어 축** | 매 사이클 무조건 강제 실행 | **글로벌 인에이블 (`en`) 지원** | 메모리 병목 대응 스톨 및 동적 전력 절감(Clock Gating) |
| **누산 경계 제어** | 전체 전역 풀 리셋만 가능 | **국소 클리어 (`clear_acc`)** | 클럭 사이클 손실 없는 새로운 벡터 내적 시퀀스 개시 |
| **합성 가능성** | 테스트벤치 전용 코드 상주 | **Pure Synthesizable RTL** | 무결한 양산형 합성 흐름 진입 및 코드 품질 최적화 |

---

## 2. 모듈 사양 명세 및 매개변수화 (Parameterization)

```verilog
module mac_v2 #(
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
)
```

* **아키텍처적 유연성**: 데이터 입력 전폭(`DATA_WIDTH`)과 최상위 누산기 비트 대역폭(`ACC_WIDTH`)을 하드웨어 매크로 파라미터로 격리 선언함으로써 정적 소스 코드의 무결한 재사용성을 확립했습니다.
* **도메인 특화 가속 가동 사양**: 해당 설계를 기반으로 탑 레이어 최적화 컴파일 옵션을 조정하는 것만으로 다음과 같은 상이한 DSA(Domain-Specific Accelerator) 실리콘 타겟으로 즉시 인스턴스화 빌드가 가능합니다.
* 초경량 신경망용 **INT4** 가속 프로세서
* 모바일 및 엣지 서버 타겟형 상용 **INT8** NPU
* 고정밀 산술 처리를 요구하는 고성능 **INT16** DSP 가속기 기판



---

## 3. 인터페이스 제어 핀 및 레지스터 평면 분석

### 3.1 글로벌 클럭 및 리셋 인터페이스

```verilog
input wire clk,
input wire rst_n, // Active-low asynchronous reset
```

* **Naming Convention**: 리셋 제어 신호선에 후속 표기된 `_n` 접미사는 전위 레벨이 `0(GND)`일 때 내부 플립플롭 청소 회로가 활성화됨을 의미하는 산업 표준 매핑 규칙입니다. 전원 스위칭 시 발생하는 고주파 기생 전하 노이즈로부터 하드웨어 내부 유한 상태 머신(FSM)을 강인하게 보호합니다.

### 3.2 글로벌 인에이블 플로우 제어 (`en`)

```verilog
input wire en,
```

* **하드웨어 제어 기능**: `en = 0` 레벨 상태가 인가되면, 하위 내부 파이프라인 레지스터들의 소스 클럭 동기 상태 전이가 원천 차단(Hold)됩니다.
* **시스템 공학적 효용성**:
1. 외부 상위 메모리 서브시스템에서 버퍼 미스가 발생했을 때 파이프라인 전체를 깨짐 없이 일시정지(Stall) 시킬 수 있습니다.
2. 다운스트림 백프레셔(Backpressure)에 실시간 대응하여 데이터 흐름 제어(Flow Control)를 이행합니다.
3. 불필요한 토글링 전류 소모를 막아 칩셋 전체의 동적 전력을 차단(Power Reduction)하는 클럭 게이팅 인프라를 형성합니다.



### 3.3 누산기 독립 클리어 인터페이스 (`clear_acc`)

```verilog
input wire clear_acc,
```

* **도입 배경**: 가속기 연산 스트림은 대수학적으로 행렬의 벡터 내적 구조인 
$$y = \sum_{i} a_i b_i$$


 식을 무수히 연쇄 이행하게 됩니다. 따라서 특정 매트릭스 도트 프로덕트 계산 경계선(Accumulation Boundary)마다 기존 누산기 레지스터 상태를 청소하고 새로운 시퀀스를 개시해야 합니다.
* **동작 원리**: 하드웨어 리셋 핀을 때리면 1 사이클이 통째로 증발하며 전역 상태가 깨지지만, `clear_acc = 1` 신호를 주면 내부 조합 논리에 의해 다음 사이클 계산 시 기존 부분합 자산을 자연스럽게 `0`으로 간주 처리하므로 속도 패널티가 소멸합니다.

---

## 4. 유효 신호 핸드셰이크 파이프라인 (Valid Handshake)

```verilog
input  wire in_valid,
output reg  acc_valid
```

현실 세계의 물리 가속 시스템 패브릭에서는 매 클럭 사이클마다 완벽하게 유효한 데이터가 공급될 수 없으며, 버블(Bubble)과 스톨이 상시 연쇄 발생합니다. 따라서 연산 데이터 버스 옆에 해당 신호가 진짜 유효한 실체인지를 대변하는 유효성 플래그선(`valid`)을 병렬 배치하는 핸드셰이크 프로토콜이 필수적입니다.

```python
# Pipeline Valid 신호 시간 동기화 추적 평면 (2-Cycle Latency)
# Cycle N:   in_valid 인가 (입력 포트 신호 유효 플래그)
# Cycle N+1: prod_valid 갱신 (Stage 1 곱셈 레지스터 동기화 정렬)
# Cycle N+2: acc_valid 출력 (Stage 2 누산기 최종 결과물 외부 리포팅)
```

본 칩셋 아키텍처는 데이터 연산의 레이턴시 지연 폭과 정확하게 동기화되어 `in_valid` 상태를 내부 플립플롭으로 전송하므로, 상위 컨트롤러가 데이터 버스트 시점을 엄격하게 통제 제어할 수 있습니다.

---

## 5. 1단계: 곱셈 파이프라인 스테이지 분석 (Stage 1 - Multiply)

```verilog
localparam PROD_WIDTH = 2 * DATA_WIDTH;
reg signed [PROD_WIDTH-1:0] prod_reg;
reg                         prod_valid;
reg                         prod_clear;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        prod_reg   <= {PROD_WIDTH{1'b0}};
        prod_valid <= 1'b0;
        prod_clear <= 1'b0;
    end else if (en) begin
        prod_reg   <= in_data * weight;
        prod_valid <= in_valid;
        prod_clear <= clear_acc & in_valid;
    end
end
```

* **물리적 차단벽 생성 의의**: 기초형 가속 코어는 `acc <= acc + (a * b)` 형태로 단일 클럭 내에 곱셈 조합 회로와 누산 가산 회로가 한 번에 결합되어 있었습니다. 이는 입력 비트 폭($16 \times 16$, $32 \times 32$ 등)이 커질수록 Multiplier 코어 자체의 물리 게이트 지연 시간 패널티에 가산기 크리티컬 패스(Critical Path)가 누적되어 타이밍 마진 위반을 초래했습니다.
* **파이프라인 분리 성과**: 곱셈 연산만을 전담하여 플립플롭 레지스터(`prod_reg`)에 강제 격리 수용함으로써 크리티컬 패스를 반절 단위로 분쇄했습니다. 이를 통해 하드웨어 전역 클럭 동작 주파수 한계선을 **`300 MHz+`** 이상 체급으로 증폭 가속화할 수 있으며, ASIC 타이밍 클로저 확보 및 FPGA $F_{max}$ 마진 확보가 극도로 용이해집니다.

---

## 6. 비트 폭 확장 및 부호 확장 하드웨어 명세 (Sign Extension)

```verilog
wire signed [ACC_WIDTH:0] prod_ext =
    {{(ACC_WIDTH-PROD_WIDTH+1){prod_reg[PROD_WIDTH-1]}}, prod_reg};
```

* **수치 해석적 메커니즘**: `PROD_WIDTH` 대역폭을 지닌 16비트 곱셈 결과 상수를 상위 32비트 가산기 버스 평면에 인가하기 위해 부호 비트 복제 연산(`Sign Extension`)을 수행하는 정적 구문입니다. 부호 있는 2의 보수 정밀도 $-15$ 규격인 `16'hFFF1` 신호가 인가되면 최상위 비트 `1`을 전폭 확장 복제 매핑하여 33비트 규격인 `33'h1_FFFF_FFF1` 형태의 신호 구조를 완성합니다.
* **여유 비트(`+1 bit`) 확보 Rationale**: 최종 목표 적재 대역인 `ACC_WIDTH`보다 정확히 1비트 더 큰 확장 버스 폭(`[ACC_WIDTH:0]`)을 설계했습니다. 이는 하위 스테이지 2 영역에서 최종 가산 연산 마감 시 가중치가 누적되며 비트 범위를 이탈하는 순간을 사전에 스캔 필터링하기 위한 공학적 포석 디바이스입니다.

---

## 7. 2단계: 누적 및 포화 연산 스테이지 분석 (Stage 2 - Accumulate)

```verilog
wire signed [ACC_WIDTH:0] acc_ext = {acc[ACC_WIDTH-1], acc};
wire signed [ACC_WIDTH:0] acc_base = prod_clear ? {(ACC_WIDTH+1){1'b0}} : acc_ext;
wire signed [ACC_WIDTH:0] acc_next_raw = acc_base + prod_ext;

wire overflow_detected = (acc_next_raw[ACC_WIDTH] != acc_next_raw[ACC_WIDTH-1]);

```

### 7.1 비지배 오버플로우 감지 수학적 원리 (Overflow Detection)

2의 보수(2's Complement) 산술 체계 하에서 부호 있는 물리 오버플로우가 터졌음을 입증할 수 있는 가장 무결한 수학적 원리는 "정상 범위를 확장한 최상위 수치 보존 비트($acc\_next\_raw[32]$)와 실제 하위 트런케이션 예정 부호 비트($acc\_next\_raw[31]$) 간의 논리적 불일치 상태"를 스캔하는 것입니다.

* 동일한 부호를 가진 대수학 상수가 합산되었으나 가산기 상한 임계선을 돌파하여 실질 부호 비트 평면이 강제 반전되는 데드락 패턴을 실시간 색출합니다.

### 7.2 포화 연산 제어 로직 (Saturation Logic)

```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        acc <= {ACC_WIDTH{1'b0}};
        overflow <= 1'b0;
        acc_valid <= 1'b0;
    end else if (en) begin
        if (prod_valid) begin
            if (overflow_detected) begin
                acc      <= acc_next_raw[ACC_WIDTH] ? ACC_MIN : ACC_MAX;
                overflow <= 1'b1;
            end else begin
                acc      <= acc_next_raw[ACC_WIDTH-1:0];
            end
        end
        acc_valid <= prod_valid;
    end
end
```

* **기초형 회로의 데이터 파괴 현상**: 이전 모델(`mac.v`)은 가산 임계 한계 돌파 시 비트 값이 강제 반전되어 양수 누계치가 극단적 음수로 변하는 사일런트 랩어라운드(Silent Wrap-around) 현상이 상시 터져 대규모 인공지능 알고리즘 정확도를 영구 파괴했습니다.
* **양산형 구조 보호 매커니즘**: 오버플로우 검출 즉시 가속 평면은 부호 상태에 따라 표현 가능한 최대 정수형 상수 상한선인 `ACC_MAX` ($+2,147,483,647$) 혹은 하한선인 `ACC_MIN` ($-2,147,483,648$) 데이터로 출력을 강제 포화 고정(`Saturation`) 시켜 알고리즘 풋프린트를 방어합니다.
* **Sticky Overflow**: 경고 플래그 신호선인 `overflow` 비트는 일단 `1`로 치솟으면 중간에 다시 정상 값으로 복귀하더라도 리셋 전원 제어가 인가되기 전까지 그 상태를 상주 홀딩하는 **Sticky 속성**을 갖도록 빌드하여, 원격 텔레메트리 디버깅 가시성을 무결하게 지원합니다.

---

## 8. 양산형 파일 컴파일 설계 규칙 및 하드웨어 토폴로지 요약

### 8.1 불순 시뮬레이션 지시어 제거

기존 모델 하단에 정적으로 내장되어 있던 가상 파형 덤프 구문(`$dumpfile`, `$dumpvars`)은 실리콘 게이트 셀 합성이 전면 불가능한 비합성성 불순 코드 품질 자산이었습니다. `mac_v2.v` 구조에서는 해당 구문을 하드웨어 내부에서 완전 소거 정돈 처리했으며, 파형 데이터 리포팅 임무는 오직 외부 검증 프레임워크인 cocotb 전용 테스트벤치(`test_mac_v2.py`) 환경줄 지시어로 이관하여 **Pure Synthesizable 양산 스펙**을 완수했습니다.

### 8.2 마이크로아키텍처 전역 토탈 가속 흐름도

```text
  [입력 버스 데이터: in_data, weight, in_valid]
                        │
                        ▼ (Clock Edge 동기 인가)
          ┌──────────────────────────┐
          │  Stage 1: Multiplier Core│
          └──────────────────────────┘
                        │
                        ▼ (비트 폭 확장 연산 수행: PROD_WIDTH)
          ┌──────────────────────────┐
          │Pipeline Register 격리 장벽│
          └──────────────────────────┘
                        │
                        ▼ (33-bit Signed Sign-Extension)
          ┌──────────────────────────┐
          │  Stage 2: Adder Accumulator│
          └──────────────────────────┘
                        │
                        ▼ (MSB 부호 정합성 스캔 및 오버플로우 감지)
          ┌──────────────────────────┐
          │ Saturation Protection Unit│
          └──────────────────────────┘
                        │
                        ▼ (포화 연산 마감 및 출력 프로토콜 정렬)
  [출력 가속 인터페이스: acc, overflow, acc_valid]
```

---

## 9. 결론 및 다음 아키텍처로의 자산 확장 기점

본 최적화 단원을 통해 분석 완료된 양산형 가속 유닛 설계 자산(`mac_v2.v`)은 주파수 마진 장악과 데이터 무결성 보호가 완벽히 결합된 상용 DSA 반도체의 표본입니다.

여기서 확보한 2-stage 파이프라인 지연 특성과 유효 신호 핸드셰이크 정렬 제어 지식은 차후 전개될 최상위 대단원인 **`Systolic Array (시스톨릭 행렬 가속 평면 그리드 패널)`** 구조체를 유기적으로 조립하고, 매 사이클 단위 내부 마이크로 제어 타이밍 윈도우를 나노초 스케일 단위로 스케줄링 제어하기 위한 가장 단단한 하드웨어 공학적 토대로 기능하게 될 것입니다.
