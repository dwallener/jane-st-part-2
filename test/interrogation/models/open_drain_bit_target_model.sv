// Non-synthesizable invented target: ACK equals one secret request bit.
`default_nettype none
module open_drain_bit_target_model #(
    parameter integer SECRET_BIT = 0
) (
    input  wire scl,
    inout  wire sda
);
  reg active = 1'b0;
  reg [3:0] bit_count = 0;
  reg [7:0] shift = 0;
  reg ack_pending = 1'b0;
  reg ack_driving = 1'b0;
  reg drive_low = 1'b0;

  assign (strong0, highz1) sda = drive_low ? 1'b0 : 1'bz;

  always @(negedge sda)
    if (scl) begin
      active <= 1'b1;
      bit_count <= 0;
      shift <= 0;
      ack_pending <= 1'b0;
      ack_driving <= 1'b0;
    end

  always @(posedge sda)
    if (scl) begin
      active <= 1'b0;
      drive_low <= 1'b0;
      ack_pending <= 1'b0;
      ack_driving <= 1'b0;
    end

  always @(posedge scl)
    if (active && !ack_driving) begin
      shift <= {shift[6:0], sda};
      if (bit_count == 7) begin
        bit_count <= 0;
        ack_pending <= 1'b1;
      end else begin
        bit_count <= bit_count + 1'b1;
      end
    end

  always @(negedge scl) begin
    if (active && ack_pending) begin
      // Address/write encoding stores request bit N at shift bit N+1.
      drive_low <= shift[SECRET_BIT + 1];
      ack_pending <= 1'b0;
      ack_driving <= 1'b1;
    end else if (ack_driving) begin
      drive_low <= 1'b0;
      ack_driving <= 1'b0;
    end
  end
endmodule
`default_nettype wire
