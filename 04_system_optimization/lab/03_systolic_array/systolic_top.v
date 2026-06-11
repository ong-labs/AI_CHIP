// systolic_top.v — 조립 모듈
//
// 역할: 4개 서브모듈을 와이어로 연결만 — 자체 로직 없음.
//   weight_loader → pe_array (weights)
//   input_skew    → pe_array (act)
//   pe_array      → output_collect (psum)
//
// FSM/제어는 외부 testbench (또는 별도 controller 모듈) 가 담당.

module systolic_top #(
    parameter ROWS = 4,
    parameter COLS = 4,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,

    // Weight load 인터페이스
    input  wire                                   weight_start,
    input  wire signed [ROWS*COLS*DATA_WIDTH-1:0] weight_matrix_flat,
    output wire                                   weight_done,

    // Activation 스트림 (parallel, skew 는 내부에서)
    input  wire signed [ROWS*DATA_WIDTH-1:0]      act_in_flat,
    input  wire                                   act_valid_in,

    // 출력
    output wire signed [COLS*ACC_WIDTH-1:0]       result_flat,
    output wire                                   valid_out
);

    // ── Weight loader → pe_array
    wire [ROWS*COLS-1:0]                   load_weight_w;
    wire signed [ROWS*COLS*DATA_WIDTH-1:0] weight_w;

    weight_loader #(
        .ROWS(ROWS), .COLS(COLS), .DATA_WIDTH(DATA_WIDTH)
    ) u_wloader (
        .clk(clk), .rst_n(rst_n),
        .start(weight_start),
        .weight_matrix_flat(weight_matrix_flat),
        .load_weight_flat(load_weight_w),
        .weight_out_flat(weight_w),
        .done(weight_done)
    );

    // ── input_skew → pe_array
    wire signed [ROWS*DATA_WIDTH-1:0] act_skewed_w;

    input_skew #(
        .ROWS(ROWS), .DATA_WIDTH(DATA_WIDTH)
    ) u_skew (
        .clk(clk), .rst_n(rst_n), .en(en),
        .act_in_flat(act_in_flat),
        .act_out_flat(act_skewed_w)
    );

    // ── pe_array (psum_top = 0)
    wire signed [COLS*ACC_WIDTH-1:0] psum_bot_w;
    wire signed [ROWS*DATA_WIDTH-1:0] act_right_w;     // unused

    pe_array #(
        .ROWS(ROWS), .COLS(COLS),
        .DATA_WIDTH(DATA_WIDTH), .ACC_WIDTH(ACC_WIDTH)
    ) u_array (
        .clk(clk), .rst_n(rst_n), .en(en),
        .load_weight_flat(load_weight_w),
        .weight_in_flat  (weight_w),
        .act_left_flat   (act_skewed_w),
        .psum_top_flat   ({(COLS*ACC_WIDTH){1'b0}}),
        .act_right_flat  (act_right_w),
        .psum_bot_flat   (psum_bot_w)
    );

    // ── pe_array → output_collect
    output_collect #(
        .COLS(COLS), .ACC_WIDTH(ACC_WIDTH)
    ) u_collect (
        .clk(clk), .rst_n(rst_n), .en(en),
        .psum_in_flat(psum_bot_w),
        .valid_in    (act_valid_in),
        .result_flat (result_flat),
        .valid_out   (valid_out)
    );

`ifndef SYNTHESIS
`ifdef DUMP_SYSTOLIC_TOP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, systolic_top);
    end
`else
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, systolic_top);
    end
`endif
`endif
`endif

endmodule
