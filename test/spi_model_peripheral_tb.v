`default_nettype none
`timescale 1ns / 1ps

module tb_spi_model_peripheral;
  reg clk = 1'b0;
  reg rst_n = 1'b0;
  reg load_valid = 1'b0;
  reg [4:0] load_address = 5'b0;
  reg [7:0] load_data = 8'b0;
  reg load_commit = 1'b0;
  reg [3:0] pin_in = 4'b1000;
  wire [3:0] pin_out;
  wire [3:0] pin_oe;
  wire model_valid;
  wire load_error;
  wire stream_causal;
  wire transfer_valid;
  wire [7:0] transfer_request;
  wire transfer_unknown;
  reg [7:0] artifact [0:21];
  integer index;
  integer bit_index;
  reg expected_bit;

  always #5 clk = ~clk;

  spi_model_peripheral dut (
      .clk(clk), .rst_n(rst_n),
      .load_valid(load_valid), .load_address(load_address),
      .load_data(load_data), .load_commit(load_commit),
      .model_valid(model_valid), .load_error(load_error),
      .pin_in(pin_in), .pin_out(pin_out), .pin_oe(pin_oe),
      .stream_causal(stream_causal), .transfer_valid(transfer_valid),
      .transfer_request(transfer_request),
      .transfer_unknown(transfer_unknown)
  );

  task fail;
    input [8*100-1:0] message;
    begin
      $display("FAIL: %0s", message);
      $finish(1);
    end
  endtask

  task write_artifact;
    begin
      for (index = 0; index < 22; index = index + 1) begin
        @(negedge clk);
        load_address = index[4:0];
        load_data = artifact[index];
        load_valid = 1'b1;
      end
      @(negedge clk);
      load_valid = 1'b0;
      load_commit = 1'b1;
      @(negedge clk);
      load_commit = 1'b0;
      #1;
    end
  endtask

  task transfer;
    input [7:0] request_byte;
    input [7:0] expected_response;
    input expected_unknown;
    begin
      // Learned mapping: clock pin 0, request pin 1, response pin 2,
      // active-low select pin 3. Mode 1 samples on the trailing edge.
      @(negedge clk);
      pin_in[3] = 1'b0;
      pin_in[0] = 1'b0;
      repeat (2) @(posedge clk);
      for (bit_index = 7; bit_index >= 0; bit_index = bit_index - 1) begin
        @(negedge clk);
        pin_in[1] = request_byte[bit_index];
        pin_in[0] = 1'b1;
        repeat (2) @(posedge clk);
        #1;
        expected_bit = expected_response[bit_index];
        if (pin_oe !== 4'b0100) fail("response pin ownership is wrong");
        if (pin_out[2] !== expected_bit) fail("wire response bit is wrong");
        @(negedge clk);
        pin_in[0] = 1'b0;
        @(posedge clk);
        #1;
        if (bit_index == 0) begin
          if (!transfer_valid) fail("completed transfer was not reported");
          if (transfer_request != request_byte)
            fail("wire request assembled incorrectly");
          if (transfer_unknown != expected_unknown)
            fail("request-family result is wrong");
        end
      end
      @(negedge clk);
      pin_in[3] = 1'b1;
      #1;
      if (pin_oe != 4'b0) fail("response pin was not released on deselect");
      repeat (2) @(posedge clk);
    end
  endtask

  initial begin
    // Python artifact: mode 1, MSB-first, response = 0x60 | request[1:0].
    {artifact[0], artifact[1], artifact[2], artifact[3], artifact[4],
     artifact[5], artifact[6], artifact[7], artifact[8], artifact[9],
     artifact[10], artifact[11], artifact[12], artifact[13], artifact[14],
     artifact[15], artifact[16], artifact[17], artifact[18], artifact[19],
     artifact[20], artifact[21]} =
        176'h445001010c9308088001020a00f0a082000042000000;

    repeat (2) @(negedge clk);
    rst_n = 1'b1;
    write_artifact();
    if (!model_valid || load_error || !stream_causal)
      fail("valid stream-causal artifact was rejected");

    transfer(8'hA7, 8'h63, 1'b0);
    transfer(8'hB7, 8'h63, 1'b1);

    // Legal model encoding, but response bit 7 depends on future request bit 0.
    {artifact[0], artifact[1], artifact[2], artifact[3], artifact[4],
     artifact[5], artifact[6], artifact[7], artifact[8], artifact[9],
     artifact[10], artifact[11], artifact[12], artifact[13], artifact[14],
     artifact[15], artifact[16], artifact[17], artifact[18], artifact[19],
     artifact[20], artifact[21]} =
        176'h44500101049308018001010a00000000000000100000;
    write_artifact();
    if (!model_valid || stream_causal)
      fail("noncausal model was not distinguished from malformed model");
    @(negedge clk);
    pin_in[3] = 1'b0;
    #1;
    if (pin_oe != 4'b0) fail("noncausal model drove a response pin");

    $display("SPI MODEL PERIPHERAL PASS");
    $finish(0);
  end
endmodule

`default_nettype wire
