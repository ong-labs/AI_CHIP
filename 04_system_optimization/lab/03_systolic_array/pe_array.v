// pe_array.v — ROWS × COLS systolic PE grid (구조만 담당, 시간 staging X)
//
// 역할:
//   - mac_prod 인스턴스 ROWS × COLS 개를 generate 로 생성
//   - 셀 간 배선만 책임 (act left→right, psum top→bottom)
//   - skew / weight load 시퀀스 / output 수집은 외부 모듈이 담당
//
// 인터페이스는 모두 flat vector (Verilog 2001 호환):
//   - load_weight_flat[i*COLS + j]            : PE(i,j) 의 load strobe
//   - weight_in_flat[(i*COLS+j+1)*DW-1 -: DW] : PE(i,j) 의 weight
//   - act_left_flat[(i+1)*DW-1 -: DW]         : row i 의 좌측 edge 입력
//   - psum_top_flat[(j+1)*AW-1 -: AW]         : col j 의 상단 edge 입력
//   - act_right_flat / psum_bot_flat          : 우측 / 하단 edge 출력

module pe_array #(
    parameter ROWS = 4,
    parameter COLS = 4,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,

    input  wire [ROWS*COLS-1:0]                   load_weight_flat,
    input  wire signed [ROWS*COLS*DATA_WIDTH-1:0] weight_in_flat,

    input  wire signed [ROWS*DATA_WIDTH-1:0]      act_left_flat,
    input  wire signed [COLS*ACC_WIDTH-1:0]       psum_top_flat,

    output wire signed [ROWS*DATA_WIDTH-1:0]      act_right_flat,
    output wire signed [COLS*ACC_WIDTH-1:0]       psum_bot_flat
);

    // 내부 wire — 2D 배열 (Verilog 2001 unpacked array of vectors)
    wire signed [DATA_WIDTH-1:0] h_act  [0:ROWS-1][0:COLS];   // [i][0]=left, [i][COLS]=right
    wire signed [ACC_WIDTH-1:0]  v_psum [0:ROWS][0:COLS-1];   // [0][j]=top,  [ROWS][j]=bot

    genvar i, j;

    // ── 좌/우 edge : flat ↔ 2D 변환
    generate
        for (i = 0; i < ROWS; i = i + 1) begin : g_h_edge
            assign h_act[i][0] = act_left_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH];
            assign act_right_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH] = h_act[i][COLS];
        end
    endgenerate

    // ── 상/하 edge : flat ↔ 2D 변환
    generate
        for (j = 0; j < COLS; j = j + 1) begin : g_v_edge
            assign v_psum[0][j] = psum_top_flat[(j+1)*ACC_WIDTH-1 -: ACC_WIDTH];
            assign psum_bot_flat[(j+1)*ACC_WIDTH-1 -: ACC_WIDTH] = v_psum[ROWS][j];
        end
    endgenerate

    // ── PE 격자 생성
    generate
        for (i = 0; i < ROWS; i = i + 1) begin : g_row
            for (j = 0; j < COLS; j = j + 1) begin : g_col
                mac_prod #(
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

`ifndef SYNTHESIS
`ifdef DUMP_PE_ARRAY
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, pe_array);
    end
`else
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, pe_array);
    end
`endif
`endif
`endif

endmodule
