`default_nettype none
`timescale 1ns / 1ps

module tb_template_pipeline;
  reg clk = 1'b0;
  reg rst_n = 1'b0;
  reg observe = 1'b0;
  reg [7:0] observe_request = 8'b0;
  reg [7:0] observe_response = 8'b0;
  reg [15:0] observe_delay = 16'b0;
  reg request_valid = 1'b0;
  reg [7:0] request_value_in = 8'b0;

  wire have_evidence;
  wire [7:0] request_mask;
  wire [7:0] request_value;
  wire [143:0] candidate_masks;
  wire delay_known;
  wire [15:0] delay_value;
  wire [7:0] evidence_count;
  wire model_complete;
  wire request_ready;
  wire response_valid;
  wire [7:0] response_value;
  wire unknown;
  wire busy;

  integer elapsed;

  always #5 clk = ~clk;

  template_learner learner (
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

  template_executor executor (
      .clk(clk),
      .rst_n(rst_n),
      .request_valid(request_valid),
      .request_value_in(request_value_in),
      .model_complete(model_complete),
      .model_request_mask(request_mask),
      .model_request_value(request_value),
      .model_candidate_masks(candidate_masks),
      .model_delay_value(delay_value),
      .request_ready(request_ready),
      .response_valid(response_valid),
      .response_value(response_value),
      .unknown(unknown),
      .busy(busy)
  );

  task fail;
    input [8*80-1:0] message;
    begin
      $display("FAIL: %0s", message);
      $finish(1);
    end
  endtask

  task add_observation;
    input [7:0] request_byte;
    input [7:0] response_byte;
    begin
      @(negedge clk);
      observe_request = request_byte;
      observe_response = response_byte;
      observe_delay = 16'd6;
      observe = 1'b1;
      @(negedge clk);
      observe = 1'b0;
    end
  endtask

  initial begin
    repeat (2) @(negedge clk);
    rst_n = 1'b1;

    add_observation(8'hA0, 8'h60);
    add_observation(8'hAF, 8'h6F);
    if (model_complete) fail("sparse evidence must remain ambiguous");
    add_observation(8'hA3, 8'h63);
    add_observation(8'hA5, 8'h65);

    #1;
    if (!model_complete) fail("training must resolve the model");
    if (request_mask !== 8'hF0 || request_value !== 8'hA0)
      fail("learned predicate is wrong");

    // The held-out A7 request is accepted and scheduled six clocks out.
    @(negedge clk);
    if (!request_ready) fail("executor must initially be ready");
    request_value_in = 8'hA7;
    request_valid = 1'b1;
    @(posedge clk);
    #1;
    request_valid = 1'b0;
    if (!busy || request_ready) fail("executor must apply backpressure while waiting");
    if (response_value !== 8'h67) fail("held-out response expression is wrong");

    elapsed = 0;
    while (!response_valid && elapsed < 7) begin
      @(posedge clk);
      #1;
      elapsed = elapsed + 1;
    end
    if (!response_valid) fail("scheduled response never arrived");
    if (elapsed != 6) fail("scheduled response arrived at wrong delay");
    if (response_value !== 8'h67) fail("scheduled response value changed");
    if (busy || !request_ready) fail("executor must be ready after response");

    // An out-of-family request is explicitly refused, not guessed.
    @(negedge clk);
    request_value_in = 8'hB7;
    request_valid = 1'b1;
    @(posedge clk);
    #1;
    request_valid = 1'b0;
    if (!unknown) fail("out-of-family request must produce unknown");
    if (busy || response_valid) fail("unknown request must not schedule a response");

    @(posedge clk);
    #1;
    if (unknown) fail("unknown must be a one-cycle pulse");

    $display("TEMPLATE PIPELINE PASS");
    $finish(0);
  end
endmodule

`default_nettype wire
