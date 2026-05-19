# 01_verilog_simulation_quickstart.md: Verilog & RTL Simulation Quickstart

**💡 선행 학습 안내 (Pre-read Guide)**
> 본 문서는 **Unit 03**의 하드웨어 컴포넌트 설계 실습인 [/03_npu_prototyping/lab/02_hardware_comp_bench.py](../03_npu_prototyping/lab/02_hardware_comp_bench.py)에 진입하기 전, 15~20분 내외로 가볍게 읽어두는 속성 퀵스타트 가이드입니다. 
> NPU 프로토타이핑에 사용되는 **핵심 Verilog 패턴, cocotb 기반의 파이썬 검증 파이프라인, 그리고 Surfer 파형(Waveform) 분석 기법**만을 압축하여 다루며, 완전한 언어 스펙을 다루지는 않습니다. 실습 시작 전 전체적인 하드웨어 설계 및 디버깅 흐름을 매끄럽게 파악하는 것을 목표로 합니다.

## 1. 한 모듈의 골격

```verilog
module mac (
    input  wire        clk,            // 클럭 (입력)
    input  wire        rst,            // 동기 리셋 (입력)
    input  wire [7:0]  in_data,        // 8-bit 부호없는 입력
    input  wire [7:0]  weight,         // 8-bit 가중치
    output reg  [31:0] acc             // 32-bit 누적 (출력, 레지스터)
);
    // 동기 회로: clk 의 rising edge 마다 동작
    always @(posedge clk) begin
        if (rst)
            acc <= 32'd0;               // 리셋 시 0
        else
            acc <= acc + (in_data * weight);  // 매 cycle 누적
    end
endmodule
```

핵심 포인트:
- `module ... endmodule` — 한 단위 회로
- `input/output` 으로 외부 인터페이스 선언
- `[N-1:0]` — N-bit 폭 (예: `[7:0]` = 8 bit)
- `wire` — 조합 회로 신호 (combinational), `reg` — 레지스터 (sequential)
- 출력에 *값을 저장*하면 `output reg`, 그냥 *연결*하면 `output wire`

## 2. always 블록의 두 종류

```verilog
// (a) 동기 회로: clk 마다 업데이트, non-blocking 할당 <=
always @(posedge clk) begin
    acc <= acc + 1;       // 다음 clock edge 에 반영
end

// (b) 조합 회로: 입력 변화 시 즉시 업데이트, blocking 할당 =
always @(*) begin
    out = a + b;          // 즉시 반영
end
```

**규칙**:
- `always @(posedge clk)` 안에서는 `<=` (non-blocking)
- `always @(*)` 또는 일반 always 안에서는 `=` (blocking)
- 섞으면 latch 또는 race condition 발생 — 흔한 함정

## 3. 비트 폭 명시 — 가장 흔한 오류

```verilog
// ❌ 잘못: 8-bit 결과에 누적하면 오버플로우
reg [7:0] bad_acc;
always @(posedge clk) bad_acc <= bad_acc + in_data * weight;
// in_data*weight = 16 bit. bad_acc 가 8 bit 라 손실.

// ✅ 정답: 누적은 더 큰 폭으로
reg [31:0] good_acc;
always @(posedge clk) good_acc <= good_acc + (in_data * weight);
// in_data*weight 자동으로 16 bit, good_acc 가 32 bit 라 안전
```

INT8 × INT8 = INT16. INT16 을 N 번 누적 → 최대 INT16 + log2(N) bits 필요. **본 코스에서는 INT8 입력 누적은 INT32 로 통일**.

## 4. 부호 있는 (signed) 곱셈

```verilog
input wire signed [7:0] in_data;          // -128 ~ 127
input wire signed [7:0] weight;
output reg  signed [31:0] acc;

always @(posedge clk) acc <= acc + (in_data * weight);
```

`signed` 키워드 없으면 unsigned 로 해석되어 음수가 큰 양수처럼 처리됨. **NPU 에서는 signed 사용 권장**.

## 5. Testbench 측 (cocotb 에서 자주 쓰는)

```verilog
// dump waveform 위해 dut 모듈 끝에 추가 (선택)
initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, mac);
end
```

cocotb 가 호출하면 `dump.vcd` 생성 → Surfer 로 열어 신호 확인.

## 6. cocotb Python 측 — 자주 쓰는 패턴

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_basic(dut):
    # 1. clock 시작 (10ns 주기 = 100 MHz)
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # 2. 리셋
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # 3. 입력 인가
    dut.in_data.value = 5
    dut.weight.value = 3
    await RisingEdge(dut.clk)

    # 4. 결과 확인
    assert int(dut.acc.value) == 15
```

## 7. 컴파일/실행 표준 Makefile

```makefile
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES = mac.v
TOPLEVEL = mac           # 시뮬할 top 모듈명
MODULE = test_mac        # cocotb 테스트 파일명 (.py 빼고)

include $(shell cocotb-config --makefiles)/Makefile.sim
```

실행:
```bash
make            # 시뮬 실행
make WAVES=1    # waveform 추가 생성 (도구별)
surfer dump.vcd &  # waveform 확인 (백그라운드)
```

## 8. Surfer 사용법 (waveform 뷰어)

cocotb 시뮬이 `dump.vcd` 를 만들면 Surfer 로 *매 사이클의 신호 변화* 를 시각화. 처음 열면 **빈 wave 영역**만 보임 — 신호를 *명시적으로 추가*해야 그래프 표시됨.

### 8.1 실행

```bash
make                      # 먼저 시뮬 (dump.vcd 생성)
surfer dump.vcd &         # 백그라운드로 GUI 띄움 (Linux/macOS/Windows-bin)
# 또는
surfer ./dump.vcd         # 절대/상대 경로 모두 OK
```

**Windows 학생 — 설치 안 했으면**: [https://app.surfer-project.org/](https://app.surfer-project.org/) 에서 *웹 버전* 사용. `dump.vcd` 파일을 브라우저에 드래그. 동일 UI, 동일 기능, 설치 불필요.

### 8.2 UI 레이아웃

```
┌──────────────────────────────────────────────────┐
│ [Menu]  File  View  ...                          │
├──────────────┬───────────────────────────────────┤
│ Variables    │                                   │
│ (Module Tree)│ Wave area                         │
│              │ (Initially empty)                 │
│ TOP          │                                   │
│ └── mac      │                                   │
│     ├── acc  │                                   │
│     ├── clk  │                                   │
│     └── ...  │                                   │
├──────────────┴───────────────────────────────────┤
│ Time scrollbar / Zoom control                    │
└──────────────────────────────────────────────────┘
```

좌측 panel 안 보이면: `View → Show variables` 또는 단축키 `Cmd+B` (macOS) / `Ctrl+B`.

### 8.3 신호 추가 (4 단계)

1. **모듈 클릭** — 좌측 트리에서 `mac` 클릭. 그 안의 신호 목록 (`acc, clk, in_data, rst, weight`) 등장.
2. **신호 추가** — 다음 셋 중 하나:
   - 신호 *더블클릭*
   - 신호 *우클릭 → Add to wave*
   - 우측 wave 영역으로 *드래그*
3. **여러 신호 한 번에**: `Shift+클릭` 또는 `Cmd/Ctrl+클릭` 으로 다중 선택 후 추가.
4. **순서 정렬**: 추가된 신호를 wave 영역에서 드래그로 위/아래 이동.

### 8.4 시간 줌 / 이동

| 단축키 | 동작 |
| --- | --- |
| `f` | Fit to view (전체 시뮬 시간 보이게) |
| `+` / `-` | 줌인 / 줌아웃 |
| 마우스 휠 | 줌인/아웃 (커서 위치 기준) |
| 드래그 (wave 영역) | 시간 축 이동 |
| `g` | Goto specific time (대화창) |

> 신호 추가했는데 *평탄한 직선* 만 보이면 거의 항상 *너무 멀리 줌인* 된 상태. `f` 한 번 누르면 전체 시뮬 시간이 보임.

### 8.5 신호 표현 형식 변경

추가된 신호 우클릭 → `Format`:
- `Decimal (signed)` — INT8/INT32 신호의 *진짜 값* (음수 포함)
- `Decimal (unsigned)` — 부호 없는 정수
- `Hex` — 16진
- `Binary` — 비트 패턴 (디버깅 시 유용)

본 코스의 `acc [31:0]` 는 *signed* 이므로 `Decimal (signed)` 권장 — 그래야 음수 누적 결과가 정상 표시됨.

### 8.6 흔한 막힘

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| Wave 영역 비어 있음 | 신호 추가 안 함 | 8.3 단계 따라 모듈 → 더블클릭 |
| 모든 신호가 평탄한 직선 | 너무 멀리 줌인 | `f` 키 또는 마우스 휠 줌아웃 |
| 좌측 panel 안 보임 | 사이드바 hidden | `Cmd+B` (또는 View 메뉴) |
| `acc` 값이 큰 양수 (음수 기대인데) | unsigned 표시 모드 | 우클릭 → Format → Decimal (signed) |
| 새로 만든 dump.vcd 안 반영 | Surfer 가 캐시 사용 | Surfer 종료 후 다시 띄우기 (또는 `r` 로 reload) |

### 8.7 명령행 자동 로드 (advanced)

매번 신호 클릭이 귀찮으면 `--state-file` 로 저장한 워크스페이스 재사용 가능. 본 코스에선 *학생이 매번 직접 추가하면서 신호 의미 익히는 게 학습 포인트* 라 굳이 안 함.

## 9. 흔한 함정

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| `unknown module` | VERILOG_SOURCES 에 .v 파일 누락 | Makefile 점검 |
| `module 'mac' not found` | TOPLEVEL 이름이 module 이름과 안 맞음 | 일치시킴 |
| 누적 결과가 작거나 wrap-around | `reg [N:0]` 폭이 작음 | INT32 또는 더 크게 |
| `assert dut.acc.value == 15` 실패 | 비교 시 `int(...)` 누락 — `LogicArray` 객체 비교 | `int(dut.acc.value)` 사용 |
| `dut.signal.value = -3` 후 부호 깨짐 | unsigned 모듈에 음수 입력 | signed 명시 또는 2's complement 변환 |
| Latch warning | `always @(*)` 에서 모든 분기에 값 할당 안 함 | `else` 또는 default 추가 |

## 10. 외부 자료 (더 깊이)

- [HDLBits](https://hdlbits.01xz.net/) — 인터랙티브 Verilog 문제 (영어)
- [ASIC World — Verilog](https://www.asic-world.com/verilog/index.html) — 표준 reference (영어)
- [Asynchronous Logic in Verilog (Korean)](https://wikidocs.net/240020) — 한국어 입문서
- [Surfer 공식 문서](https://surfer-project.org/) — waveform 뷰어 가이드

## 11. 이어질 실습에서 *안* 쓰는 것

- `initial` 블록 (testbench 외) — 합성 안 됨
- `for` 루프 (제한적 사용 가능하지만 본 코스 회차에서는 회피)
- SystemVerilog 고급 기능 (`interface`, `package`, `logic` 타입) — 일부 시뮬레이터 미지원
- formal verification — 별도 도구 필요

## 💡 참고 사항 (Notes)

### 1. 프로젝트 아카이브 연결 고리 (A-L Linkage)

* **이론 분석 및 가이드 (Analysis)**:
  * [02_mac_modeling_report.md](../03_npu_prototyping/analysis/02_mac_modeling_report.md): 본 퀵스타트 가이드에서 학습한 동기식 디지털 회로 구조와 Accumulator 비트 폭 확장 설계 원칙이 실제 하드웨어 MAC Unit 컴포넌트 모델에 어떻게 투영되는지 전력/에너지 비용 모델 분석 보고서와 연계하여 확인하실 수 있습니다.

* **실습 소스 코드 (Lab)**:
  * [02_hardware_comp_bench.py](../03_npu_prototyping/lab/02_hardware_comp_bench.py): 본 가이드에서 정립한 Verilog 제약 규칙 및 cocotb 테스트벤치 구동 패턴을 직접 베이스로 삼아, 정수형 연산 정합성을 소프트웨어 레벨에서 다이내믹하게 실측 검증하고 3단계 구조 메모리 계층(Register-SRAM-DRAM)의 물리 비용을 시뮬레이션하는 실습 소스 코드 아카이브입니다.

### 2. 하드웨어 검증 수립 (Verification Insight)

* 문법의 단순 암기를 넘어 파이썬 소프트웨어 모델(What to compute)과 Verilog RTL 하드웨어 동작 모델(How to compute over time) 간의 추상화 격차를 이해하고, cocotb 연동 환경을 통해 매 사이클(Cycle-by-cycle) 단위 내부 신호 파형의 변화를 Surfer 뷰어로 관찰 디버깅하는 역량은 고성능 NPU 아키텍처를 설계하는 아키텍트의 가장 강력한 기초 자산이 됩니다.