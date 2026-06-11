// Production-style systolic MAC cell (TPU-leaning).
//
// 실제 NPU/TPU 의 MAC 셀에 가까운 형태 — mac_v2.v 의 saturation/overflow flag 를
// 의도적으로 제거. 입력 quantization 단계에서 range 보장한다고 가정.
//
// 특징:
//   1. Weight stationary       — weight_reg 에 한 번 로드, 여러 activation 재사용
//   2. Activation propagation  — act_in → act_out 1 cycle 지연 (옆 셀로 전달)
//   3. Partial sum chain       — psum_in + (act × weight) → psum_out (아래 셀로)
//   4. No saturation/overflow  — INT32 누적 폭으로 미리 막음 (1024 MAC 까지 안전)
//   5. Enable                  — clock gating 효과, idle 시 동적 전력 절감
//   6. Active-low reset        — 산업 표준
//   7. Parameterized widths    — INT4/INT8/INT16 재사용
//   8. Synthesis-clean         — VCD dump 는 `ifndef SYNTHESIS` 가드

module mac_prod #(
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          en,

    // Weight 로드 — matmul 시작 시 1회 strobe
    input  wire                          load_weight,
    input  wire signed [DATA_WIDTH-1:0]  weight_in,

    // Activation : left → right
    input  wire signed [DATA_WIDTH-1:0]  act_in,
    output reg  signed [DATA_WIDTH-1:0]  act_out,

    // Partial sum : top → bottom
    input  wire signed [ACC_WIDTH-1:0]   psum_in,
    output reg  signed [ACC_WIDTH-1:0]   psum_out
);

    reg signed [DATA_WIDTH-1:0] weight_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            weight_reg <= {DATA_WIDTH{1'b0}};
            act_out    <= {DATA_WIDTH{1'b0}};
            psum_out   <= {ACC_WIDTH{1'b0}};
        end else if (en) begin
            if (load_weight) begin
                weight_reg <= weight_in;
            end
            act_out  <= act_in;
            psum_out <= psum_in + (act_in * weight_reg);
        end
    end

`ifndef SYNTHESIS
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, mac_prod);
    end
`endif
`endif

endmodule
