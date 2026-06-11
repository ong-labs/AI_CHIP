// Reference: signed INT8 × INT8 MAC with INT32 accumulator
//
// Single multiply-accumulate unit:
//   acc <- acc + (in_data * weight)   on every rising clock edge
//
// Width discipline:
//   - inputs are signed 8-bit  (-128..127)
//   - product is naturally signed 16-bit
//   - accumulator is signed 32-bit (auto sign-extension when added)

module mac (
    input  wire                clk,
    input  wire                rst,
    input  wire signed  [7:0]  in_data,
    input  wire signed  [7:0]  weight,
    output reg  signed  [31:0] acc
);
    always @(posedge clk) begin
        if (rst)
            acc <= 32'sd0;
        else
            acc <= acc + (in_data * weight);
    end

    // Waveform dump for GTKWave (`make WAVES=1` 또는 cocotb 환경변수)
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, mac);
    end
endmodule
