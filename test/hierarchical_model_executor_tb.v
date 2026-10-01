`default_nettype none
`timescale 1ns / 1ps

module tb_hierarchical_model_executor;
  reg clk = 1'b0;
  reg rst_n = 1'b0;
  reg load_valid = 1'b0;
  reg [4:0] load_address = 5'b0;
  reg [7:0] load_data = 8'b0;
  reg load_commit = 1'b0;
  reg request_valid = 1'b0;
  reg [7:0] request_value = 8'b0;
  wire model_valid;
  wire load_error;
  wire request_ready;
  wire response_valid;
  wire [7:0] response_value;
  wire unknown;
  wire busy;
  wire [1:0] select_pin;
  wire [1:0] clock_pin;
  wire [1:0] request_pin;
  wire [1:0] response_pin;
  wire select_active_level;
  wire clock_idle_level;
  wire sample_trailing;
  wire bit_reverse_equivalent;
  reg [7:0] artifact [0:21];
  integer index;

  always #5 clk = ~clk;

  hierarchical_model_executor dut (
      .clk(clk), .rst_n(rst_n),
      .load_valid(load_valid), .load_address(load_address),
      .load_data(load_data), .load_commit(load_commit),
      .model_valid(model_valid), .load_error(load_error),
      .request_valid(request_valid), .request_value(request_value),
      .request_ready(request_ready), .response_valid(response_valid),
      .response_value(response_value), .unknown(unknown), .busy(busy),
      .select_pin(select_pin), .clock_pin(clock_pin),
      .request_pin(request_pin), .response_pin(response_pin),
      .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level),
      .sample_trailing(sample_trailing),
      .bit_reverse_equivalent(bit_reverse_equivalent)
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

  task issue_request;
    input [7:0] value;
    begin
      @(negedge clk);
      request_value = value;
      request_valid = 1'b1;
      @(posedge clk);
      #1;
      request_valid = 1'b0;
    end
  endtask

  initial begin
    {artifact[0], artifact[1], artifact[2], artifact[3], artifact[4],
     artifact[5], artifact[6], artifact[7], artifact[8], artifact[9],
     artifact[10], artifact[11], artifact[12], artifact[13], artifact[14],
     artifact[15], artifact[16], artifact[17], artifact[18], artifact[19],
     artifact[20], artifact[21]} =
        176'h44500101089308088001020a00f0a082000042000000;

    repeat (2) @(negedge clk);
    rst_n = 1'b1;
    write_artifact();

    if (!model_valid || load_error) fail("valid Python artifact was rejected");
    if (!request_ready) fail("loaded executor is not ready");
    if (select_pin != 3 || clock_pin != 0 || request_pin != 1 || response_pin != 2)
      fail("packed physical pin roles decoded incorrectly");
    if (select_active_level != 0 || clock_idle_level != 0 ||
        sample_trailing != 0 || bit_reverse_equivalent != 1)
      fail("physical flags decoded incorrectly");

    issue_request(8'hA7);
    if (!response_valid || response_value != 8'h63)
      fail("serialized model did not generalize to held-out request");
    if (busy || unknown) fail("zero-delay recognized request has wrong status");

    issue_request(8'hB7);
    if (!unknown || response_valid) fail("out-of-family request was not refused");

    @(negedge clk);
    load_address = 0;
    load_data = 8'h00;
    load_valid = 1'b1;
    @(negedge clk);
    load_valid = 1'b0;
    load_commit = 1'b1;
    @(posedge clk);
    #1;
    load_commit = 1'b0;
    if (model_valid || !load_error) fail("corrupt artifact was admitted");

    $display("HIERARCHICAL MODEL EXECUTOR PASS");
    $finish(0);
  end
endmodule

`default_nettype wire
