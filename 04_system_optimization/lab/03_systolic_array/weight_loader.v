// weight_loader.v — Parallel weight distribution (1-cycle broadcast)
//
// 역할:
//   - start=1 펄스 입력 → 다음 cycle 에 모든 PE 에 load_weight 펄스 + weight 값 전달
//   - done 신호로 완료 알림
//
// 단순화 가정:
//   - 모든 PE 동시 로드 (1 cycle)
//   - 더 현실적인 TPU 식 column-by-column 로드는 future work
//
// 인터페이스:
//   - weight_matrix_flat : ROWS×COLS×DW 비트, [(i*COLS+j+1)*DW-1 -: DW] = W(i,j)
//   - load_weight_flat   : ROWS×COLS 비트 strobe (pe_array 로 직결)
//   - weight_out_flat    : weight_matrix_flat 을 그대로 forward

module weight_loader #(
    parameter ROWS = 4,
    parameter COLS = 4,
    parameter DATA_WIDTH = 8
) (
    input  wire clk,
    input  wire rst_n,
    input  wire start,
    input  wire signed [ROWS*COLS*DATA_WIDTH-1:0] weight_matrix_flat,

    output reg  [ROWS*COLS-1:0]                   load_weight_flat,
    output reg  signed [ROWS*COLS*DATA_WIDTH-1:0] weight_out_flat,
    output reg                                    done
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            load_weight_flat <= {(ROWS*COLS){1'b0}};
            weight_out_flat  <= {(ROWS*COLS*DATA_WIDTH){1'b0}};
            done             <= 1'b0;
        end else begin
            if (start) begin
                load_weight_flat <= {(ROWS*COLS){1'b1}};   // 모든 PE 동시 load
                weight_out_flat  <= weight_matrix_flat;
                done             <= 1'b0;
            end else begin
                load_weight_flat <= {(ROWS*COLS){1'b0}};   // 1 cycle 후 strobe 해제
                done             <= load_weight_flat[0];   // 직전 cycle 에 load 했으면 done
            end
        end
    end

`ifndef SYNTHESIS
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, weight_loader);
    end
`endif
`endif

endmodule
