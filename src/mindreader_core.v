/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// TinyTapeout-facing integration of the bounded autonomous SPI mindreader.
// uio[3:0] is the anonymous protocol bus. The core remains passive until a
// learned model passes timing, causality, direction, and ownership gates.
module mindreader_core (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire [7:0] dedicated_in,
    output wire [7:0] dedicated_out,
    input  wire [7:0] bidir_in,
    output wire [7:0] bidir_out,
    output wire [7:0] bidir_oe
);

  wire discover_enable = enable && dedicated_in[0];
  wire learn_enable = enable && dedicated_in[1];
  wire promote = enable && dedicated_in[2];
  wire ownership_granted = enable && dedicated_in[3];
  wire activate = enable && dedicated_in[4];
  wire revoke = dedicated_in[5];
  wire clear_fault = dedicated_in[6];
  wire contradiction = dedicated_in[7];

  wire [3:0] protocol_in = bidir_in[3:0];
  wire [3:0] raw_protocol_out;
  wire [3:0] raw_protocol_oe;
  wire physical_complete;
  wire direction_resolved;
  wire frozen_model_valid;
  wire drive_enable;
  wire [7:0] evidence_count;
  wire [2:0] supervisor_state;
  wire [2:0] fault_reason;
  wire promotion_rejected;
  wire transfer_valid;
  wire [7:0] transfer_request;
  wire transfer_unknown;
  wire [1:0] select_pin;
  wire [1:0] clock_pin;
  wire [1:0] data_a_pin;
  wire [1:0] data_b_pin;
  wire select_active_level;
  wire clock_idle_level;
  wire sample_trailing;

  wire timing_observed;
  wire timing_safe;
  wire timing_violation;
  wire timing_admissible = timing_observed && timing_safe && !timing_violation;

  // The first polyglot-front-end primitive observes all eight anonymous pins,
  // even though the bounded behavioral learner below still consumes uio[3:0].
  // There is intentionally no electrical path from this profiler to pad OE.
  wire [7:0] activity_mask;
  wire activity_seen;
  wire observation_ready;
  wire bus_quiet;

  passive_bus_profiler #(.QUIET_CYCLES(16'd64)) bus_profiler (
      .clk(clk), .rst_n(rst_n), .observe_enable(enable),
      .pin_sample(bidir_in), .activity_mask(activity_mask),
      .activity_seen(activity_seen),
      .observation_ready(observation_ready), .bus_quiet(bus_quiet)
  );

  wire mismatch_now;
  wire contention_drive_allow;
  wire contention_fault;
  // mismatch_now gates the pad OE combinationally through drive_allow. Only
  // the registered fault feeds the supervisor, avoiding a combinational loop
  // through drive_enable while preserving immediate electrical release.
  wire contention = contention_fault;

  autonomous_spi_mindreader mindreader (
      .clk(clk), .rst_n(rst_n),
      .discover_enable(discover_enable), .learn_enable(learn_enable),
      .promote(promote), .timing_safe(timing_admissible),
      .ownership_granted(ownership_granted), .activate(activate),
      .revoke(revoke), .contradiction(contradiction),
      .contention(contention), .clear_fault(clear_fault),
      .pin_in(protocol_in), .pin_out(raw_protocol_out),
      .pin_oe(raw_protocol_oe), .physical_complete(physical_complete),
      .direction_resolved(direction_resolved),
      .frozen_model_valid(frozen_model_valid), .drive_enable(drive_enable),
      .evidence_count(evidence_count), .supervisor_state(supervisor_state),
      .fault_reason(fault_reason), .promotion_rejected(promotion_rejected),
      .transfer_valid(transfer_valid), .transfer_request(transfer_request),
      .transfer_unknown(transfer_unknown), .inferred_select_pin(select_pin),
      .inferred_clock_pin(clock_pin), .inferred_data_a_pin(data_a_pin),
      .inferred_data_b_pin(data_b_pin),
      .inferred_select_active_level(select_active_level),
      .inferred_clock_idle_level(clock_idle_level),
      .inferred_sample_trailing(sample_trailing)
  );

  spi_timing_guard timing_guard (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(learn_enable && physical_complete),
      .pin_sample(protocol_in), .select_pin(select_pin),
      .clock_pin(clock_pin), .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level),
      .sample_trailing(sample_trailing), .minimum_half_ticks(8'd1),
      .minimum_select_ticks(8'd1), .timing_observed(timing_observed),
      .timing_safe(timing_safe), .timing_violation(timing_violation)
  );

  pin_contention_monitor #(.WIDTH(4)) contention_monitor (
      .clk(clk), .rst_n(rst_n), .clear_fault(clear_fault),
      .monitor_enable(drive_enable), .drive_requested(drive_enable),
      .pin_in(protocol_in), .pin_out(raw_protocol_out),
      .pin_oe(raw_protocol_oe), .mismatch_now(mismatch_now),
      .drive_allow(contention_drive_allow),
      .contention_fault(contention_fault)
  );

  assign dedicated_out = {
      promotion_rejected,
      contention_fault,
      timing_admissible,
      bus_quiet,
      drive_enable,
      frozen_model_valid,
      direction_resolved,
      physical_complete
  };
  assign bidir_out = {4'b0000, raw_protocol_out};
  assign bidir_oe = {
      4'b0000,
      raw_protocol_oe & {4{enable && contention_drive_allow}}
  };

  wire _unused = &{
      1'b0, bidir_in[7:4], evidence_count, supervisor_state, fault_reason,
      transfer_valid, transfer_request, transfer_unknown, data_a_pin,
      data_b_pin, timing_observed, activity_mask, activity_seen,
      observation_ready
  };

endmodule

`default_nettype wire
