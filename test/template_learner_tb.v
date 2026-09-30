`default_nettype none
`timescale 1ns / 1ps

module tb_template_learner;

  reg clk = 0;
  reg rst_n = 0;
  reg observe = 0;
  reg [7:0] observe_request = 0;
  reg [7:0] observe_response = 0;
  reg [15:0] observe_delay = 0;
  wire have_evidence;
  wire [7:0] request_mask;
  wire [7:0] request_value;
  wire [143:0] candidate_masks;
  wire delay_known;
  wire [15:0] delay_value;
  wire [7:0] evidence_count;
  wire model_complete;

  template_learner dut (
      .clk(clk),
      .rst_n(rst_n),
      .observe(observe),
      .observe_request(observe_request),
      .observe_response(observe_response),
      .observe_delay(observe_delay),
      .have_evidence(have_evidence),
      .request_mask(request_mask),
      .request_value(request_value),
      .candidate_masks(candidate_masks),
      .delay_known(delay_known),
      .delay_value(delay_value),
      .evidence_count(evidence_count),
      .model_complete(model_complete)
  );

  always #5 clk = ~clk;

  task add_observation;
    input [7:0] request_value_in;
    input [7:0] response_value_in;
    input [15:0] delay_value_in;
    begin
      @(negedge clk);
      observe_request = request_value_in;
      observe_response = response_value_in;
      observe_delay = delay_value_in;
      observe = 1'b1;
      @(negedge clk);
      observe = 1'b0;
      #1;
    end
  endtask

  task expect_slice;
    input integer output_bit;
    input integer candidate_index;
    reg [17:0] expected;
    begin
      expected = 18'b1 << candidate_index;
      if (candidate_masks[output_bit * 18 +: 18] !== expected) begin
        $display("FAIL: output bit %0d candidates=%h expected=%h",
                 output_bit,
                 candidate_masks[output_bit * 18 +: 18],
                 expected);
        $finish(1);
      end
    end
  endtask

  initial begin
    repeat (2) @(negedge clk);
    rst_n = 1'b1;

    add_observation(8'hA0, 8'h60, 16'd6);
    add_observation(8'hAF, 8'h6F, 16'd6);

    if (request_mask !== 8'hF0 || request_value !== 8'hA0) begin
      $display("FAIL: request predicate mask=%h value=%h", request_mask, request_value);
      $finish(1);
    end
    if (!delay_known || delay_value !== 16'd6 || evidence_count !== 8'd2) begin
      $display("FAIL: timing/evidence state");
      $finish(1);
    end
    if (model_complete) begin
      $display("FAIL: sparse evidence resolved prematurely");
      $finish(1);
    end

    add_observation(8'hA3, 8'h63, 16'd6);
    add_observation(8'hA5, 8'h65, 16'd6);

    if (!model_complete) begin
      $display("FAIL: separating evidence did not resolve model");
      $finish(1);
    end
    expect_slice(0, 2);  // copy request[0]
    expect_slice(1, 4);  // copy request[1]
    expect_slice(2, 6);  // copy request[2]
    expect_slice(3, 8);  // copy request[3]
    expect_slice(4, 0);  // constant 0
    expect_slice(5, 1);  // constant 1
    expect_slice(6, 1);  // constant 1
    expect_slice(7, 0);  // constant 0

    add_observation(8'hA8, 8'h68, 16'd7);
    if (delay_known || model_complete) begin
      $display("FAIL: conflicting delay did not invalidate model timing");
      $finish(1);
    end

    @(negedge clk);
    rst_n = 1'b0;
    @(negedge clk);
    #1;
    if (have_evidence || evidence_count !== 0 || candidate_masks !== 0) begin
      $display("FAIL: reset did not clear learned state");
      $finish(1);
    end

    $display("TEMPLATE LEARNER PASS");
    $finish(0);
  end

endmodule

`default_nettype wire

