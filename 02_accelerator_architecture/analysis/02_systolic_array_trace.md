# 02_systolic_array_trace.md: Hardware Mapping Analysis of Core NPU Logic

본 문서는 [02_systolic_array_report.md](./02_systolic_array_report.md)의 성능 데이터와 [02_systolic_array_scrutiny.md](./02_systolic_array_scrutiny.md)의 동작 논리를 바탕으로, [02_tpu_ws_systolic_bench.py](../lab/02_tpu_ws_systolic_bench.py) 시뮬레이터의 로직을 실제 하드웨어 설계 사양으로 매핑합니다. **앞선 분석들이 '현상'을 다루었다면, 본 문서는 그 현상을 Verilog/VHDL로 구현하기 위한 '구조'를 정의합니다.**

---

## 1. Systolic Array 아키텍처의 전제와 철학

### 1.1 연산의 전제 조건

본 아키텍처의 진정한 가치는 단순 연산이 아닌 데이터 재사용(Data Reuse)을 통한 고성능 GEMM(General Matrix Multiplication) 가속에 있습니다. 한 번 메모리에서 읽어온 데이터를 수많은 PE가 공유하게 함으로써, AI 연산의 고질적 문제인 메모리 대역폭(Memory Bandwidth) 병목 현상을 근본적으로 해결합니다.

* **구조**: `입력 행렬(Input) * 가중치 행렬(Weight) = 결과 행렬(Result)`
* 이 형태를 만족할 때만 PE(Processing Element) 배열을 통한 병렬 최적화가 가능해집니다.

### 1.2 시스템 해석의 관점

시스톨릭 어레이는 결과 중심적인 아키텍처입니다.

* **결과론적 해석**: 결과 행렬의 각 원소는 행의 크기(N)만큼 사이클이 지나야 비로소 계산되기 시작합니다. 시스템은 이 지연 시간(Latency)을 허용하는 대신, 파이프라인을 통해 처리량(Throughput)을 극대화하는 방향으로 설계됩니다.

---

## 2. `step()` 함수: 하드웨어 상태 전이(State Transition) 모델링

`step()` 메소드는 가속기의 한 클럭(Cycle) 동안 발생하는 물리적 변화를 시뮬레이션합니다.

```python
def step(self, left_inputs: np.ndarray) -> np.ndarray:
    # 1. 계산 (Compute): 현재 사이클의 부분합 누산
    ps_out = self.pe_ps_in + self.pe_input * self.weights
    
    # 2. 결과 배출 (Emit): 맨 마지막 행의 부분합을 bottom 벡터로 복사하여 배출
    bottom = ps_out[-1].copy()

    # 3. 입력 데이터 이동 (Shift Right): 첫 번째 열을 비우고 오른쪽으로 Shift
    new_pe_input = np.zeros_like(self.pe_input)
    new_pe_input[:, 1:] = self.pe_input[:, :-1]
    new_pe_input[:, 0] = left_inputs # 외부에서 주입된 입력 벡터 배치

    # 4. 부분합 이동 (Shift Down): 계산 결과를 아래쪽으로 Shift
    new_pe_ps_in = np.zeros_like(self.pe_ps_in)
    new_pe_ps_in[1:] = ps_out[:-1] # 최상단 행은 항상 0 유입

    # 5. 상태 업데이트: 다음 사이클을 위해 시스템 구성요소에 대입
    self.pe_input = new_pe_input
    self.pe_ps_in = new_pe_ps_in
    
    self.cycle += 1
    return bottom
```

---

## 3. `run()` 함수: 인덱스 스케줄링 및 파이프라인 최적화

`run()` 메소드는 전체 연산 사이클($M+K+N$) 동안 데이터가 언제 유입되고 언제 배출되는지를 제어합니다.

### 3.1 입력 스케줄링 (조건 패턴 1)

* **논리**: `m = t - k`
* **설명**: 입력 데이터가 대각선 형태로 주입되어야 하므로, 사이클($t$)과 PE의 행 번호($k$)를 연산하여 입력 행렬의 유효 요소를 선택합니다. 전체 사이클의 절반 정도까지는 이 조건에 따라 입력을 주입하며, 나머지는 입력 없이 내부 계산(Pipeline Drain)을 수행합니다.

### 3.2 출력 매핑 (조건 패턴 2)
첫 번째 결과 $C[0,0]$이 나오기까지의 지연 시간(Latency)은 입력 데이터가 행(Row)을 통과하는 시간($1$)과 열(Column)을 따라 누적되는 시간($K-1$)인 **Accumulation Depth**에 의해 결정됩니다.

* **논리**: `t_out = m + K + n`
* **설명**: `bottom` 벡터에서 유효한 결과가 생성되는 시점입니다. 하드웨어 설계 시 $N$ 사이클(코드에서는 $K$로 표현)의 지연 이후부터 비로소 유효한 데이터가 배출됩니다.
* **최적화**: 수집된 `bottom` 값을 최종 출력 행렬에 순차적으로 반영함으로써, 파이프라인 구조를 극대화하고 연산 비용을 압도적으로 최적화합니다.

---

## 4. 하드웨어 구현 및 마이크로아키텍처 매핑 (Hardware Realization & Microarchitecture Mapping)

본 파이썬 시뮬레이션의 로직은 실제 NPU 설계 시 다음과 같은 하드웨어 블록으로 직결됩니다.

### 4.1 하드웨어 설계로의 전이 (Verilog/VHDL 매핑)

1. **PE(Processing Element)**: `ps_out` 계산 로직은 각 PE 내부의 **MAC 유닛**이 됩니다.
> * **Expert's Insight**: 본 시뮬레이션은 곱셈과 덧셈을 한 사이클로 가정하지만, 실제 고클럭 설계에서는 MAC 유닛 자체를 **2~3단계의 파이프라인(Pipeline Stages)**으로 쪼개어 설계하기도 합니다. 이 경우 전체 레이턴시 공식은 $M + K + N - 1$에 **MAC 파이프라인 깊이만큼의 오프셋**이 추가되어야 하며, 이는 아키텍처 설계 시 정밀한 타이밍 시뮬레이션이 필요한 이유입니다.
2. **Shift Register**: `pe_input`과 `pe_ps_in`의 이동 로직은 플립플롭(Flip-flop) 기반의 **시프트 레지스터**로 설계되어 매 클럭마다 데이터를 인접 PE로 전송합니다.
3. **Control Logic**: `run()` 함수의 인덱스 조건문들은 하드웨어의 전체 동작 상태를 제어하는 FSM(Finite State Machine)과 제어 신호가 됩니다.

### 4.2 제어 경로(Control Path) 및 물리적 설계 전략

실제 RTL 설계 시 `run()` 함수의 추상적인 제어 로직은 다음과 같은 물리적 실체로 매핑됩니다.

* **Input Skewing Registers**: `m = t - k` 로직은 하드웨어에서 단순한 연산이 아닙니다. 이는 각 PE 행(Row)에 입력이 도달하기 전 물리적인 시차를 생성하는 **지연 레지스터(Delay Flip-flops)** 체인으로 구현됩니다.
* **Valid/Enable 전파**: 실제 하드웨어에서는 데이터가 PE에 도착하는 정확한 시점에 맞춰 연산을 활성화해야 합니다. 이를 위해 데이터와 나란히 흐르는 **'Valid' 플래그** 혹은 **'Enable' 신호 전파 로직**이 설계에 포함되어 제어의 정밀도를 보장합니다.

---

## 5. 결론

본 시뮬레이션의 구현은 **NPU의 핵심 로직을 설계한 것과 동일한 가치**를 지닙니다. 이러한 로직을 Verilog 혹은 VHDL로 설계하면 실제 AI 반도체의 연산 가속기가 완성되며, 이는 단순 소프트웨어 최적화를 넘어 하드웨어 수준에서 연산 비용을 최소화하는 최상위 단계의 최적화입니다.

---

## 💡 참고 사항 (Notes)

* 본 문서에서 정의된 **Input Skewing Register**와 **Valid 전파 로직**은 **Unit 03: NPU Prototyping**의 Verilog 설계 단계에서 제어부(Control Path)의 핵심 설계도로 활용됩니다.
* 알고리즘의 인덱스(`m = t - k`)를 하드웨어 FSM으로 변환하는 과정이 본 설계 패키지의 최종 목적지입니다.
