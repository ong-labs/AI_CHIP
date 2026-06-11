// output_collect.v — Bottom row psum capture + valid tracking
//
// 역할:
//   - pe_array 의 hex 출력 (psum_bot_flat) 을 register 에 캡처
//   - valid_in 을 1 cycle 지연시켜 valid_out 으로 전달
//   - (de-skew 가 필요한 응용은 추후 확장 — 현재는 raw capture)
//
// 가장 단순한 구현 — 핵심은 *array 와 외부 인터페이스 분리*.
// 더 정교한 동작이 필요해지면 (deskew, accumulator 누적 등) 이 모듈만 교체.

module output_collect #(
    parameter COLS = 4,
    parameter ACC_WIDTH = 32
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire signed [COLS*ACC_WIDTH-1:0] psum_in_flat,
    input  wire                             valid_in,
    output reg  signed [COLS*ACC_WIDTH-1:0] result_flat,
    output reg                              valid_out
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result_flat <= {(COLS*ACC_WIDTH){1'b0}};
            valid_out   <= 1'b0;
        end else if (en) begin
            result_flat <= psum_in_flat;
            valid_out   <= valid_in;
        end
    end

`ifndef SYNTHESIS
`ifndef NO_VCD_DUMP
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, output_collect);
    end
`endif
`endif

endmodule
