`default_nettype none
`timescale 1ns / 1ps

module tb_supervisor_capture;
  reg clk = 0;
  reg rst_n = 0;
  reg evidence_present = 0;
  reg model_complete = 0;
  reg direction_resolved = 0;
  reg stream_causal = 0;
  reg timing_safe = 0;
  reg ownership_granted = 0;
  reg activate = 0;
  reg revoke = 0;
  reg contradiction = 0;
  reg contention = 0;
  reg clear_fault = 0;
  wire [2:0] state;
  wire passive;
  wire model_admitted;
  wire drive_enable;
  wire [2:0] fault_reason;

  reg capture_enable = 0;
  reg capture_clear = 0;
  reg [3:0] pin_sample = 0;
  reg pop = 0;
  wire trace_valid;
  wire [7:0] event_delta;
  wire [3:0] event_sample;
  wire [3:0] event_changed;
  wire [2:0] event_count;
  wire overflow;
  wire evidence_valid;

  always #5 clk = ~clk;

  mindreader_supervisor supervisor (
      .clk(clk), .rst_n(rst_n), .evidence_present(evidence_present),
      .model_complete(model_complete), .direction_resolved(direction_resolved),
      .stream_causal(stream_causal), .timing_safe(timing_safe),
      .ownership_granted(ownership_granted), .activate(activate),
      .revoke(revoke), .contradiction(contradiction), .contention(contention),
      .clear_fault(clear_fault), .state(state), .passive(passive),
      .model_admitted(model_admitted), .drive_enable(drive_enable),
      .fault_reason(fault_reason)
  );

  edge_trace_capture #(.DEPTH(4), .DELTA_BITS(8)) capture (
      .clk(clk), .rst_n(rst_n), .capture_enable(capture_enable),
      .clear(capture_clear), .pin_sample(pin_sample), .pop(pop),
      .valid(trace_valid), .event_delta(event_delta),
      .event_sample(event_sample), .event_changed(event_changed),
      .event_count(event_count), .overflow(overflow),
      .evidence_valid(evidence_valid)
  );

  task fail;
    input [8*100-1:0] message;
    begin $display("FAIL: %0s", message); $finish(1); end
  endtask

  task tick;
    begin @(posedge clk); #1; end
  endtask

  initial begin
    repeat (2) tick();
    if (!passive || drive_enable || state != 0) fail("reset must be passive");
    rst_n = 1;

    evidence_present = 1;
    tick();
    if (state != 1 || !passive) fail("evidence must enter candidate state");
    model_complete = 1;
    direction_resolved = 1;
    stream_causal = 1;
    timing_safe = 1;
    tick();
    if (state != 2 || !model_admitted || !passive)
      fail("safe model must be admitted but passive");
    activate = 1;
    ownership_granted = 1;
    tick();
    if (state != 3 || !drive_enable) fail("authorized model did not activate");

    // Combinational fail-safe: revoke disables drive before a clock edge.
    revoke = 1;
    #1;
    if (drive_enable || !passive) fail("revoke did not disable drive immediately");
    tick();
    if (state != 2) fail("revoke must return to admitted passive state");
    revoke = 0;
    activate = 0;
    contention = 1;
    tick();
    if (state != 4 || fault_reason != 2 || !passive)
      fail("contention must latch a passive fault");
    contention = 0;
    clear_fault = 1;
    tick();
    clear_fault = 0;
    if (state != 0) fail("cleared fault must restart observation");

    // Trace capture establishes a baseline, then stores lossless edge records.
    capture_enable = 1;
    pin_sample = 4'b0011;
    tick();
    tick();
    pin_sample = 4'b0111;
    tick();
    if (!trace_valid || event_count != 1 || event_delta != 2 ||
        event_sample != 4'b0111 || event_changed != 4'b0100)
      fail("first edge record is wrong");
    pin_sample = 4'b1110;
    tick();
    if (event_count != 2) fail("second edge was not recorded");
    pop = 1;
    tick();
    pop = 0;
    if (event_count != 1 || event_sample != 4'b1110 || event_changed != 4'b1001)
      fail("FIFO pop did not expose second event");

    // Fill beyond capacity without reading; overflow poisons all evidence.
    pin_sample = 4'b0000; tick();
    pin_sample = 4'b0001; tick();
    pin_sample = 4'b0010; tick();
    pin_sample = 4'b0011; tick();
    if (!overflow || evidence_valid) fail("trace loss was silently accepted");
    capture_clear = 1;
    tick();
    capture_clear = 0;
    if (overflow || !evidence_valid || event_count != 0)
      fail("capture clear did not restore empty valid state");

    $display("SUPERVISOR CAPTURE PASS");
    $finish(0);
  end
endmodule

`default_nettype wire
