// Reference: production-leaning MAC unit (강화판)
//
// 기본 mac.v 대비 8가지 개선:
//   1. Parameterized DATA_WIDTH / ACC_WIDTH  — INT4/INT8/INT16 재사용 가능
//   2. Active-low reset (rst_n)              — 산업 표준
//   3. Enable 신호 (en)                       — stall / power saving
//   4. Clear accumulator (clear_acc)          — 새 dot product 시퀀스 시작
//   5. Valid 신호 pipeline (in_valid → acc_valid)  — 외부 모듈과 handshake
//   6. 2-stage pipeline (곱 → 누적)           — 고주파 (>300 MHz) 동작 가능
//   7. Saturation + overflow flag             — silent wrap 방지
//   8. `initial` 블록 없음                    — 합성 가능, testbench 가 dump 담당

module mac_v2 #(
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  wire                          clk,
    input  wire                          rst_n,      // active-low reset
    input  wire                          en,         // global enable
    input  wire                          clear_acc,  // 이번 입력부터 acc 새로 시작
    input  wire signed [DATA_WIDTH-1:0]  in_data,
    input  wire signed [DATA_WIDTH-1:0]  weight,
    input  wire                          in_valid,   // 입력이 유효함
    output reg  signed [ACC_WIDTH-1:0]   acc,
    output reg                           overflow,   // saturation 발생 표시
    output reg                           acc_valid   // acc 가 유효한 결과임
);

    localparam PROD_WIDTH = 2 * DATA_WIDTH;
    localparam signed [ACC_WIDTH-1:0] ACC_MAX = {1'b0, {(ACC_WIDTH-1){1'b1}}};  // 2^(ACC_WIDTH-1) - 1
    localparam signed [ACC_WIDTH-1:0] ACC_MIN = {1'b1, {(ACC_WIDTH-1){1'b0}}};  // -2^(ACC_WIDTH-1)

    // ===========================================================
    // Stage 1: 곱 (1 cycle latency)
    // ===========================================================
    reg signed [PROD_WIDTH-1:0] prod_reg;
    reg                          prod_valid;
    reg                          prod_clear;

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

    // 곱 결과를 ACC_WIDTH+1 비트로 sign-extend (overflow 감지용 1비트 여유)
    wire signed [ACC_WIDTH:0] prod_ext =
        {{(ACC_WIDTH-PROD_WIDTH+1){prod_reg[PROD_WIDTH-1]}}, prod_reg};

    // ===========================================================
    // Stage 2: 누적 + saturation (1 cycle latency)
    // ===========================================================
    wire signed [ACC_WIDTH:0] acc_ext = {acc[ACC_WIDTH-1], acc};                  // sign-extend acc to 33-bit
    wire signed [ACC_WIDTH:0] acc_base = prod_clear ? {(ACC_WIDTH+1){1'b0}} : acc_ext;
    wire signed [ACC_WIDTH:0] acc_next_raw = acc_base + prod_ext;

    // Overflow 감지: 33-bit 결과의 sign bit (bit 32) 와 32-bit truncation 시 sign bit (bit 31) 가 다르면 overflow
    wire overflow_detected = (acc_next_raw[ACC_WIDTH] != acc_next_raw[ACC_WIDTH-1]);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc       <= {ACC_WIDTH{1'b0}};
            overflow  <= 1'b0;
            acc_valid <= 1'b0;
        end else if (en) begin
            if (prod_valid) begin
                if (overflow_detected) begin
                    acc      <= acc_next_raw[ACC_WIDTH] ? ACC_MIN : ACC_MAX;
                    overflow <= 1'b1;
                end else begin
                    acc      <= acc_next_raw[ACC_WIDTH-1:0];
                    // overflow 는 sticky — 한 번 1 이면 reset 까지 유지
                end
            end
            acc_valid <= prod_valid;
        end
    end

`ifndef SYNTHESIS
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, mac_v2);
    end
`endif

endmodule
