// input_skew.v — Activation staircase delay buffer
//
// 역할:
//   - ROWS 개 입력 중 row i 를 i cycle 지연시켜 출력
//   - systolic array 의 wave 정렬 (모든 K-index 데이터가 동시에 PE 에 도착)
//
// 동작 (예: ROWS=3):
//   cycle 0:  in[0]=a, in[1]=b, in[2]=c  →  out[0]=a, out[1]=?, out[2]=?
//   cycle 1:  in[0]=d, in[1]=e, in[2]=f  →  out[0]=d, out[1]=b, out[2]=?
//   cycle 2:  in[0]=g, in[1]=h, in[2]=i  →  out[0]=g, out[1]=e, out[2]=c
//
// 구현:
//   - row i 는 길이 i 의 shift register
//   - row 0 은 pass-through (delay 0)

module input_skew #(
    parameter ROWS = 4,
    parameter DATA_WIDTH = 8
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire signed [ROWS*DATA_WIDTH-1:0] act_in_flat,
    output wire signed [ROWS*DATA_WIDTH-1:0] act_out_flat
);

    genvar i, k;

    generate
        for (i = 0; i < ROWS; i = i + 1) begin : g_row
            if (i == 0) begin : g_passthrough
                // row 0 : pass-through (delay 0)
                assign act_out_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH]
                     = act_in_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH];
            end else begin : g_delay
                // row i : i-stage shift register → pe_array (edge-BEFORE-NBA read) 기준 i 사이클 지연
                // (cocotb read = AFTER NBA 는 i-1 사이클 지연으로 보임)
                reg signed [DATA_WIDTH-1:0] pipe [0:i-1];
                integer m;

                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin
                        for (m = 0; m < i; m = m + 1) pipe[m] <= {DATA_WIDTH{1'b0}};
                    end else if (en) begin
                        pipe[0] <= act_in_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH];
                        for (m = 1; m < i; m = m + 1) pipe[m] <= pipe[m-1];
                    end
                end

                assign act_out_flat[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH] = pipe[i-1];
            end
        end
    endgenerate

`ifndef SYNTHESIS
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, input_skew);
    end
`endif
`endif

endmodule
