# 03_systolic_array_grid.md: Systolic Array Interconnect Architecture Analysis Report Based on 2D Generate Grid and Virtual Wire Topology

본 보고서는 시스톨릭 아키텍처 계층의 핵심 컴포넌트인 [**pe_array.v**](../lab/03_systolic_array/pe_array.v) 하드웨어 소스 코드를 바탕으로 작성되었습니다. 본 모듈은 가속기 시스템 내부에서 독자적인 산술 연산 알고리즘을 개별적으로 정의하거나, 유한 상태 머신(FSM) 제어 로직을 내장하거나, 실시간 데이터 런타임 스케줄링을 통제하지 않는 철저한 **"구조적 조립 및 물리 배선도(Structural Interconnect & Wiring Schematic)"**의 정체성을 가집니다. 프로세싱 엘리먼트(Processing Element, PE) 코어 셀들을 2차원 평면 공간 상에 자동 복제 배치하고, 이들 간의 가로/세로 데이터 이동 통로를 엮어주는 가속 패브릭의 물리적 연결 메커니즘을 마이크로아키텍처 관점에서 해체 분석합니다.

---

## 1. 모듈의 본질과 독보적인 추상화 정체성

하드웨어 공학 관점에서 `pe_array` 모듈의 유일한 사명은 **"독립 컴포넌트들을 격자 공간에 배치하고 신호 무결성을 갖추어 상호 연결하는 것"**입니다. 

* **제어의 전면 배제**: 내부적으로 데이터의 유효성을 판별하는 핸드셰이크 제어나 타이밍 스큐(Skew) 조정, 가중치 버스트 카운터 등의 순차 제어 로직이 일절 배제되어 있습니다. 해당 통제 제어 기능은 최상위 오케스트레이션 레이어(`systolic_top.v`) 및 외부 컨트롤러 자산으로 이관되어 동작합니다.
* **조립 모듈로서의 정체성**: 리프 셀인 `mac_prod` 연산 장치를 행($ROWS$)과 열($COLS$) 단위 격자로 투입하여, 옆 칸 PE와 위 아랫 칸 PE의 물리 포트 간 와이어 결합 관계만을 기하학적으로 서술한 순수 토폴로지 아셈블리 모듈입니다.

---

## 2. 하드웨어 사양 명세 및 파라미터화 (Parameterization)

```verilog
module pe_array # (
    parameter ROWS = 4,
    parameter COLS = 4,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) ( ... );
```

가변 정밀도 가속기 평면을 유연하게 합성(Synthesis)해 내기 위해 4대 핵심 컴파일 타임 매개변수를 전면 탑재하고 있습니다.

* **`ROWS` / `COLS**`: 2차원 시스톨릭 연산 평면의 물리적 행 개수와 열 개수를 규정합니다. 기본 사양 명세에 의거하여 **$4 \times 4$ 구조체 가속 그리드**를 자동 형성합니다.
* **`DATA_WIDTH`**: 입력 피처 맵 액티베이션 데이터 및 가중치(Weight) 파라미터 버스의 비트 폭 전폭을 정의하는 인자이며, 정수형 표준 가동 제원인 **8비트(INT8)** 정밀도를 추종합니다.
* **`ACC_WIDTH`**: 유한 비트 폭 환경 하에서의 수치적 정확성을 사수하고 오버플로우를 원천 차단하기 위해 확장 설계된 부분합(Partial Sum) 누산기 전폭 비트 대역폭을 뜻하며, 산업 표준 사양인 32비트(INT32)로 락(Lock) 선언되어 있습니다.

---

## 3. 입출력 포트 평면 및 Flat 버스 구조 분석

Verilog 2001 표준 호환성 및 다차원 배열 포트 선언 제약을 우회하기 위해, 외부 인터페이스 버스는 다차원 행렬 데이터를 한 줄로 길게 늘어뜨린 **`Flat Vector Bus`** 양식을 전폭적으로 채택하고 있습니다.

```text
[Flat Vector Bus 비트 스트림 구조 명세 평면]
1. load_weight_flat : MSB [PE 3,3] ─── ... ─── [PE 0,1] ─── [PE 0,0] LSB  (16-bit 전폭)
2. act_left_flat    : MSB [Row 3]   ─── [Row 2] ─── [Row 1] ─── [Row 0] LSB  (32-bit 전폭)
3. psum_top_flat    : MSB [Col 3]   ─── [Col 2] ─── [Col 1] ─── [Col 0] LSB  (128-bit 전폭)
```

### 3.1 `load_weight_flat` (가중치 로드 제어선 버스)

* `input wire [ROWS*COLS-1:0] load_weight_flat`
* $4 \times 4$ 사양 기준 정확히 **16비트** 물리 대역을 점유합니다. 그리드 평면 내의 각 개별 독립 연산 유닛 $PE_{(i,j)}$에게 "이번 클럭 상승 에지에 입력 데이터 버스로부터 가중치를 내부 상주 레지스터로 락인(Lock-in) 적재하라"고 명령하는 단일 비트 스트로브(Strobe) 신호선들의 집합체입니다. 인덱스 변환 규칙에 의거하여 비트 0은 $PE_{(0,0)}$, 비트 1은 $PE_{(0,1)}$, 최종 비트 15는 $PE_{(3,3)}$ 물리 셀 포트에 직결 정렬됩니다.

### 3.2 `weight_in_flat` (전역 가중치 데이터 로드 버스)

* `input wire signed [ROWS*COLS*DATA_WIDTH-1:0] weight_in_flat`
* $4 \times 4$ 구조체에 8비트 정밀도가 매핑되어 총 128비트($16 \times 8$)의 초광대역 물리 데이터 패스를 장악합니다. 행렬 연산 개시 전, 모든 PE 유닛에게 주입할 가중치 파라미터 벡터 상수를 한 줄로 언팩(Unpack) 전개하여 전달하는 소스 대역입니다.

### 3.3 `act_left_flat` (좌측 경계 액티베이션 입력 버스)

* `input wire signed [ROWS*DATA_WIDTH-1:0] act_left_flat`
* 각 행(Row)의 서부 좌측 최외곽 경계면 PE들에게 실시간 입력 피처 맵 데이터 스크림을 인가하는 전송 패스로서, $4 \times 8 = $ **32비트** 대역폭으로 기판에 배선됩니다. 리틀 엔디안 규칙에 의거하여 `[7:0]` 구간은 Row 0, `[15:8]` 구간은 Row 1, 최종 `[31:24]` 구간은 Row 3의 좌측 입력 노드로 안착합니다.

### 3.4 `psum_top_flat` (상단 경계 부분합 입력 버스)

* `input wire signed [COLS*ACC_WIDTH-1:0] psum_top_flat`
* 각 열(Column)의 북부 상단 최외곽 경계면 PE들로부터 중간 누산 결과를 수용하는 통로이며, 32비트 고정밀도 채널 4개 분량인 총 **128비트($4 \times 32$)** 대역을 점유합니다. 일반적인 행렬곱 독립 기동 시에는 누산기 최초 기점을 0으로 통제하기 위해 최상위 컴파일러 단에서 고정형 제로 버스인 `{(COLS*ACC_WIDTH){1'b0}}` 상수를 강제 주입 배선합니다.

---

## 4. 내부 가상 와이어 토폴로지 기하학 분석 (Internal Interconnect Nodes)

2차원 격자 평면 공간 상에서 가로축 데이터 시프트와 세로축 부분합 체인을 완벽하게 정렬 결합해 내기 위해, 내부 가상 와이어 공간의 물리적 매트릭스 차원을 정밀 확장 설계했습니다.

```text
[h_act 가로축 데이터선 전개 기하학 구조]
입구선 노드 0        셀 연산 가속 공간 평면 영역         출구선 노드 4
h_act[i][0]  ──►  PE(i,0)  ──►  PE(i,1)  ──►  PE(i,2)  ──►  PE(i,3)  ──►  h_act[i][4]
```

### 4.1 가로 방향 액티베이션 전송 배선망 (`h_act`)

* `wire signed [DATA_WIDTH-1:0] h_act [0:ROWS-1][0:COLS];`
* **차원 확장 이유 ($[0:COLS]$)**: 격자 평면에 일렬로 조립 배치된 PE 코어 유닛이 4개($COLS=4$)일 때, 가속 데이터가 안전하게 횡단 통과하기 위해서는 '좌측 최초 진입 입구 노드 1개'와 '셀 간 상호 연결 통로 3개', 그리고 '우측 최종 하차 출구 노드 1개'를 합산하여 정확히 총 5개의 공간적 타이밍 격자점(Node)이 요구되기 때문입니다. 따라서 배열 인덱스는 정확히 `0`부터 `4`까지 전개 확장됩니다.

### 4.2 세로 방향 부분합 체인 배선망 (`v_psum`)

* `wire signed [ACC_WIDTH-1:0] v_psum [0:ROWS][0:COLS-1];`
* **차원 확장 이유 ($[0:ROWS]$)**: 상단 경계선 제로 버스를 수용하는 북쪽 진입 입구면 노드 0번 영역부터 시작하여, 남쪽 방향으로 4단계의 PE 가산기 셀 단계를 관통 체인 물리 결합을 완료한 후, 최하단 남측 경계선 출구 노드로 데이터를 전출시키기 위해 세로축 차원을 `0`부터 `4`까지 확장 지정했습니다.

---

## 5. 외곽 경계선 결합 조건식 분석 (Edge Boundary Processing)

Flat 포트 신호선과 내부 2차원 가상 와이어 노드 간의 물리적 정합성을 동기화하는 정적 매핑(`assign`) 논리 구조식 구조입니다.

### 5.1 수평축 경계 처리 (Horizontal Edge Boundary)

```verilog
generate
    for (i = 0; i < ROWS; i = i + 1) begin : g_h_edge
        assign h_act[i][0] = act_left_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH];
        assign act_right_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH] = h_act[i][COLS];
    end
endgenerate
```

* **수학적 인덱싱 해체**: $i=0$ (첫 번째 행) 기동 시, 포트 대역 `act_left_flat[7:0]`의 전위 상태가 즉시 가상 와이어 노드 `h_act[0][0]` 주소선으로 직결 주입됩니다. 반대쪽 극단면에서는 마지막 4번째 가속 유닛의 시프트 출력물인 `h_act[0][4]` 전하가 전외 출력 포트 평면의 `act_right_flat[7:0]` 대역 버스로 완벽하게 토스 아웃 바이패스 처리됩니다.

### 5.2 수직축 경계 처리 (Vertical Edge Boundary)

```verilog
generate
    for (j = 0; j < COLS; j = j + 1) begin : g_v_edge
        assign v_psum[0][j] = psum_top_flat[(j+1)*ACC_WIDTH-1 -: ACC_WIDTH];
        assign psum_bot_flat[(j+1)*ACC_WIDTH-1 -: ACC_WIDTH] = v_psum[ROWS][j];
    end
endgenerate
```

* **수학적 인덱싱 해체**: 최상단 인풋 피드선 구조인 `v_psum[0][j]` 평면 영역에는 외부 상단 psum flat 버스 비트 정밀도 격자가 1:1 직결 결합을 마감하며, 최종 4단 적재 누산 완료 기점인 `v_psum[4][j]` 노드의 내부 물리 신호는 최종 행렬곱 산출물 출력 버스인 `psum_bot_flat` 포트 평면으로 무결하게 하차 기록됩니다.

---

## 6. 2차원 Generate 그리드 복제 및 인스턴스 매핑 분석

하드웨어 컴파일러에게 공간적 하드웨어 배열 구조 복제를 명령하는 최하단 조립 커널 엔진부입니다. `generate` 2중 루프 제어문을 가동하여 $4 \times 4 = 16$개의 유효 연산 소자를 실리콘 공간 상에 완벽하게 정렬 배치합니다.

```verilog
generate
    for (i = 0; i < ROWS; i = i + 1) begin : g_row
        for (j = 0; j < COLS; j = j + 1) begin : g_col
            mac_prod # (
                .DATA_WIDTH(DATA_WIDTH),
                .ACC_WIDTH (ACC_WIDTH)
            ) pe (
                .clk        (clk),
                .rst_n      (rst_n),
                .en         (en),
                .load_weight(load_weight_flat[i*COLS + j]),
                .weight_in  (weight_in_flat[(i*COLS + j + 1)*DATA_WIDTH-1 -: DATA_WIDTH]),
                .act_in     (h_act[i][j]),
                .act_out    (h_act[i][j+1]),
                .psum_in    (v_psum[i][j]),
                .psum_out   (v_psum[i+1][j])
            );
        end
    end
endgenerate
```

### 6.1 Flat 인덱싱 및 가중치 슬라이싱 산술 메커니즘

2차원 좌표 격자 $PE_{(i,j)}$를 1차원 평탄화 일렬 버스로 정밀 치환 전개하기 위해 매핑 산술 관계식인 **`i * COLS + j`** 변환 공식을 코어 내부 커널에 수식 적용하고 있습니다.

* **물리적 인덱스 변환 이행 실례 ($PE_{(2,3)}$ 유닛 가동 시)**:
행 인덱스 $i=2$, 열 인덱스 $j=3$ 상태일 때, 로드 스트로브 라인은 $2 \times 4 + 3 = $ 정확히 `load_weight_flat[11]` 번 핀 주소와 와이어 웰딩 결합을 성립시킵니다. 동시에, 주입 가중치 데이터 슬라이싱 기법은 하향식 가변 비트 슬라이싱 지시어(`-: DATA_WIDTH`) 매커니즘에 의거하여 다음과 같이 유도됩니다.

$$\text{Bit\_High} = (2 \times 4 + 3 + 1) \times 8 - 1 = 95$$

$$\text{Bit\_Low} = 95 - 8 + 1 = 88$$

따라서 초광대역 버스 내부의 국소 주소 영역인 `weight_in_flat[95:88]` 비트 패턴 대역만이 $PE_{(2,3)}$ 코어 셀 내부 입력 포트로 오차 없이 정밀 바인딩 스케일링 필터링 처리됩니다.

### 6.2 하드웨어 Concurrency 제어를 위한 공간 와이어 체이닝

* **수평 시프트 매핑**: 현재 위치 셀의 입력 노드인 `.act_in(h_act[i][j])`선선과 우향 전송 출력단 포트인 `.act_out(h_act[i][j+1])`이 정렬 결합되어, 클럭의 매 상승 에지 타이밍마다 데이터 전하가 서쪽에서 동쪽 방향(왼쪽 $\rightarrow$ 오른쪽)으로 순차 횡단 전이 유도되는 물리 패스를 구축합니다.
* **수직 부분합 체인 매핑**: 위 레이어 소자로부터 전출된 psum 연산선 대역인 `.psum_in(v_psum[i][j])` 상태 자산을 인가받아 산술 연산 마감 후, 남향 출력단 포트 버스 평면인 `.psum_out(v_psum[i+1][j])` 노드로 토스 다운 시켜 줌으로써 누산 데이터 흐름이 북쪽에서 남쪽 방향(위쪽 $\rightarrow$ 아래쪽)으로 강력하게 폭포수처럼 관통 낙하 연쇄 가산되는 인프라 토폴로지를 완성합니다.

---

## 7. 가속기 전역 데이터플로우 토폴로지 평면 구조도 ($4 \times 4$ 기준)

본 모듈의 배선 공식을 시각적으로 도식화한 전역 공간 토폴로지 레이아웃 도면입니다.

```text
       [psum_top_flat 제로 버스 입력단 주입선선 영역]
              │          │          │          │
              ▼          ▼          ▼          ▼
 act_left  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐
 ──Row 0──►│PE_00├───►│PE_01├───►│PE_02├───►│PE_03├──► act_right_flat
              │          │          │          │       (Row 0 Output)
              ▼          ▼          ▼          ▼
 act_left  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐
 ──Row 1──►│PE_10├───►│PE_11├───►│PE_12├───►│PE_13├──► act_right_flat
              │          │          │          │       (Row 1 Output)
              ▼          ▼          ▼          ▼
 act_left  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐
 ──Row 2──►│PE_20├───►│PE_21├───►│PE_22├───►│PE_23├──► act_right_flat
              │          │          │          │       (Row 2 Output)
              ▼          ▼          ▼          ▼
 act_left  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐
 ──Row 3──►│PE_30├───►│PE_31├───►│PE_32├───►│PE_33├──► act_right_flat
              │          │          │          │       (Row 3 Output)
              ▼          ▼          ▼          ▼
       [psum_bot_flat 최종 누산 완료 행렬 출력단 버스 평면 영역]
```

---

## 8. 결론: 하드웨어 배선 오케스트레이션의 총평

$$\boxed{\text{"pe\_array 모듈은 독자 연산을 전개하지 않는 대신, 가속기의 X축 및 Y축 물리 데이터 통로를 획정하는 실리콘 신경망 지도이다."}}$$

수치 해석 분석을 완결하며 도출한 `pe_array` 모듈의 공학적 본질은 명확합니다. 하드웨어 설계 내에서 "행렬 연산 알고리즘이나 상태 머신 제어를 전면 배제하되, 오직 하드웨어 Concurrency 구현을 극대화하기 위해 2차원 공간 상에 가로축 액티베이션 시프트선과 세로축 부분합 누산 체인 버스를 한 치의 단선 없이 정밀 오케스트레이션 웰딩 결합해 낸 물리 연결 패브릭 자산"으로 정의됩니다.

본 보고서에서 검증 완료된 물리 배선 평면도는 향후 다차원 입력 데이터 스큐 가동 시나리오 및 최상위 시스템 제어부 설계 주차에서 나노초 스케일 타이밍 격자 단위 스케줄링 흐름을 통제하기 위한 가장 핵심적인 물리적 골격 거점으로 기능하게 될 것입니다.
