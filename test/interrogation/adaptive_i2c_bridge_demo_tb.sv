`timescale 1ns/1ps
`default_nettype none

// Deterministic waveform demonstration of the complete raw-wire path:
// passive frames -> role/evidence inference -> proposal -> active probes ->
// one surviving behavioral hypothesis. SECRET_BIT exists only in the target.
module adaptive_i2c_bridge_demo_tb;
  reg clk = 0;
  reg rst_n = 0;
  reg observe_enable = 0;
  reg start = 0;
  reg authorize = 0;
  reg abort_request = 0;
  reg host_scl_low = 0;
  reg host_sda_low = 0;
  reg [2:0] demo_phase = 0;

  localparam [2:0] CLOCK_PIN = 3'd2;
  localparam [2:0] DATA_PIN = 3'd5;
  localparam integer SECRET_BIT = 5;

  wire [7:0] pin_in;
  wire [7:0] pin_out;
  wire [7:0] pin_oe;
  wire passive_ready;
  wire passive_accepted;
  wire proposal_valid;
  wire [6:0] proposal_request;
  wire busy;
  wire probe_done;
  wire resolved;
  wire contradiction;
  wire timed_out;
  wire revoked;
  wire [4:0] candidate_count;
  wire winner_invert;
  wire [2:0] winner_bit;
  wire [2:0] inferred_clock_pin;
  wire [2:0] inferred_data_pin;

  integer probe_count = 0;
  integer wait_count = 0;

  tri scl;
  tri sda;
  pullup (weak1) scl_pullup(scl);
  pullup (weak1) sda_pullup(sda);
  assign (strong0, highz1) scl = host_scl_low ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = host_sda_low ? 1'b0 : 1'bz;
  assign (strong0, highz1) scl = pin_oe[CLOCK_PIN] ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = pin_oe[DATA_PIN] ? 1'b0 : 1'bz;
  assign pin_in = {2'b11, sda, 2'b11, scl, 2'b11};

  open_drain_bit_target_model #(.SECRET_BIT(SECRET_BIT)) target (
      .scl(scl), .sda(sda)
  );

  adaptive_i2c_interrogation_bridge dut (
      .clk(clk), .rst_n(rst_n), .observe_enable(observe_enable),
      .start(start), .authorize(authorize), .abort_request(abort_request),
      .pin_in(pin_in), .pin_out(pin_out), .pin_oe(pin_oe),
      .passive_ready(passive_ready), .passive_accepted(passive_accepted),
      .proposal_valid(proposal_valid), .proposal_request(proposal_request),
      .busy(busy), .probe_done(probe_done), .resolved(resolved),
      .contradiction(contradiction), .timed_out(timed_out),
      .revoked(revoked), .candidate_count(candidate_count),
      .winner_invert(winner_invert), .winner_bit(winner_bit),
      .inferred_clock_pin(inferred_clock_pin),
      .inferred_data_pin(inferred_data_pin)
  );

  always #5 clk = ~clk;

  task tick;
    begin
      @(posedge clk);
      #1;
    end
  endtask

  task lines;
    input scl_low;
    input sda_low;
    begin
      host_scl_low = scl_low;
      host_sda_low = sda_low;
      tick();
    end
  endtask

  task passive_frame;
    input [7:0] value;
    integer bit_no;
    begin
      observe_enable = 1'b1;
      lines(0, 0);
      lines(0, 1);  // START
      for (bit_no = 7; bit_no >= 0; bit_no = bit_no - 1) begin
        lines(1, !value[bit_no]);
        lines(0, !value[bit_no]);
        lines(1, !value[bit_no]);
      end
      lines(1, 0);  // release data for ACK/NACK
      lines(0, 0);
      lines(1, 0);
      lines(1, 1);
      lines(0, 1);
      lines(0, 0);  // STOP
      observe_enable = 1'b0;
      tick();
      tick();
      tick();
    end
  endtask

  task fail;
    input [8*120-1:0] message;
    begin
      $display("FAIL: %0s", message);
      $finish(1);
    end
  endtask

  initial begin
    $dumpfile("test/interrogation/adaptive_i2c_interrogation.vcd");
    $dumpvars(0, clk, rst_n, demo_phase, observe_enable, passive_ready,
              passive_accepted, host_scl_low, host_sda_low, scl, sda,
              pin_in, pin_oe, authorize, start, busy, probe_done,
              proposal_valid, proposal_request, candidate_count, resolved,
              winner_invert, winner_bit, inferred_clock_pin,
              inferred_data_pin, contradiction, timed_out, revoked,
              dut.interrogator.candidate_mask,
              dut.interrogator.learner.search_request);

    repeat (2) tick();
    rst_n = 1'b1;
    tick();

    demo_phase = 3'd1;  // passive request 0: every candidate predicts NACK
    passive_frame(8'h00);
    demo_phase = 3'd2;  // passive request 0x7f: every candidate predicts ACK
    passive_frame(8'hfe);

    if (candidate_count != 7 || resolved)
      fail("expected seven-way passive ambiguity");
    if (inferred_clock_pin != CLOCK_PIN || inferred_data_pin != DATA_PIN)
      fail("passive frontend inferred wrong pins");

    demo_phase = 3'd3;  // sequential information-gain search
    while (!proposal_valid) begin
      tick();
      wait_count = wait_count + 1;
      if (wait_count > 130)
        fail("proposal search timeout");
    end

    demo_phase = 3'd4;  // authorized closed-loop interrogation
    authorize = 1'b1;
    while (!resolved) begin
      start = 1'b1;
      tick();
      start = 1'b0;
      while (!probe_done)
        tick();
      if (timed_out || revoked || contradiction)
        fail("active probe fault");
      probe_count = probe_count + 1;
      tick();
      wait_count = 0;
      while (!resolved && !proposal_valid) begin
        tick();
        wait_count = wait_count + 1;
        if (wait_count > 130)
          fail("proposal rescan timeout");
      end
      if (probe_count > 3)
        fail("probe budget exceeded");
    end

    demo_phase = 3'd5;  // resolved
    authorize = 1'b0;
    repeat (8) tick();
    if (winner_invert || winner_bit != SECRET_BIT)
      fail("resolved wrong target behavior");
    if (pin_oe != 0)
      fail("bus not released");
    $display("ADAPTIVE I2C WAVEFORM PASS: probes=%0d winner_bit=%0d",
             probe_count, winner_bit);
    $finish(0);
  end
endmodule

`default_nettype wire
