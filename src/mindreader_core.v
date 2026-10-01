/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// TinyTapeout-facing integration of the bounded autonomous protocol mindreader.
// Passive structural and UART-like candidates coexist with the executable SPI
// learner. The core remains passive until a learned SPI model passes timing,
// causality, direction, and ownership.
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

  // ui[7] enters a passive status window unless ui[4] explicitly requests a
  // contradiction. Status uses ui[3:2] and ui[6:5] as a four-bit page address
  // and suppresses every ordinary control side effect.
  wire status_mode = enable && dedicated_in[7] && !dedicated_in[4];
  wire [3:0] status_page = {dedicated_in[3:2], dedicated_in[6:5]};
  wire discover_enable = enable && !status_mode && dedicated_in[0];
  wire learn_enable = enable && !status_mode && dedicated_in[1];
  wire promote = enable && !status_mode && dedicated_in[2];
  wire ownership_granted = enable && !status_mode && dedicated_in[3];
  wire activate = enable && dedicated_in[4];
  wire revoke = dedicated_in[5] && !status_mode;
  wire clear_fault = dedicated_in[6] && !status_mode;
  wire contradiction = enable && dedicated_in[7] && dedicated_in[4];

  wire [7:0] protocol_in = bidir_in;
  wire [7:0] raw_protocol_out;
  wire [7:0] raw_protocol_oe;
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
  wire [2:0] select_pin;
  wire [2:0] clock_pin;
  wire [2:0] data_a_pin;
  wire [2:0] data_b_pin;
  wire select_active_level;
  wire clock_idle_level;
  wire sample_trailing;

  wire timing_observed;
  wire timing_safe;
  wire timing_violation;
  wire timing_admissible = timing_observed && timing_safe && !timing_violation;

  // The polyglot-front-end primitive independently observes all eight pins.
  // There is intentionally no electrical path from this profiler to pad OE.
  wire [7:0] activity_mask;
  wire activity_seen;
  wire observation_ready;
  wire bus_quiet;
  wire [7:0] quiet_age;

  passive_bus_profiler #(.QUIET_CYCLES(16'd64)) bus_profiler (
      .clk(clk), .rst_n(rst_n), .observe_enable(enable),
      .pin_sample(bidir_in), .activity_mask(activity_mask),
      .activity_seen(activity_seen),
      .observation_ready(observation_ready), .bus_quiet(bus_quiet),
      .quiet_age(quiet_age)
  );

  wire router_ready;
  wire [7:0] router_activity_mask;
  wire [7:0] async_candidate_mask;
  wire [7:0] clock_candidate_mask;
  wire [7:0] select_candidate_mask;
  wire [2:0] candidate_classes;
  wire router_insufficient;
  wire router_ambiguous;

  serial_hypothesis_router hypothesis_router (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(discover_enable || learn_enable),
      .pin_sample(bidir_in), .ready(router_ready),
      .activity_mask(router_activity_mask),
      .async_candidate_mask(async_candidate_mask),
      .clock_candidate_mask(clock_candidate_mask),
      .select_candidate_mask(select_candidate_mask),
      .candidate_classes(candidate_classes),
      .insufficient(router_insufficient), .ambiguous(router_ambiguous)
  );

  wire uart_ready;
  wire uart_candidate_valid;
  wire uart_candidate_ambiguous;
  wire [2:0] uart_pin;
  wire uart_pin_valid;
  wire uart_idle_level;
  wire [14:0] uart_period_mask;
  wire [4:0] uart_width_mask;
  wire [2:0] uart_parity_mask;
  wire [1:0] uart_stop_mask;
  wire [9:0] uart_candidate_count;
  wire [8:0] uart_decoded_value;

  uart_symbol_hypothesis uart_hypothesis (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(discover_enable || learn_enable),
      .pin_sample(bidir_in), .ready(uart_ready),
      .candidate_valid(uart_candidate_valid),
      .candidate_ambiguous(uart_candidate_ambiguous),
      .uart_pin(uart_pin), .uart_pin_valid(uart_pin_valid),
      .idle_level(uart_idle_level), .bit_period_mask(uart_period_mask),
      .data_width_mask(uart_width_mask), .parity_mask(uart_parity_mask),
      .stop_count_mask(uart_stop_mask),
      .candidate_count(uart_candidate_count),
      .decoded_value(uart_decoded_value)
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

  pin_contention_monitor #(.WIDTH(8)) contention_monitor (
      .clk(clk), .rst_n(rst_n), .clear_fault(clear_fault),
      .monitor_enable(drive_enable), .drive_requested(drive_enable),
      .pin_in(protocol_in), .pin_out(raw_protocol_out),
      .pin_oe(raw_protocol_oe), .mismatch_now(mismatch_now),
      .drive_allow(contention_drive_allow),
      .contention_fault(contention_fault)
  );

  wire [7:0] normal_status = {
      promotion_rejected,
      contention_fault,
      timing_admissible,
      bus_quiet,
      drive_enable,
      frozen_model_valid,
      direction_resolved,
      physical_complete
  };
  wire [7:0] structural_status = {
      router_ambiguous,
      router_insufficient,
      bus_quiet,
      router_ready,
      activity_seen,
      candidate_classes
  };
  reg [7:0] paged_status;
  always @* begin
    case (status_page)
      4'h0: paged_status = router_activity_mask;
      4'h1: paged_status = quiet_age;
      4'h2: paged_status = structural_status;
      4'h3: paged_status = clock_candidate_mask;
      4'h4: paged_status = uart_candidate_count[7:0];
      4'h5: paged_status = {uart_ready, uart_candidate_valid,
                            uart_candidate_ambiguous, uart_pin_valid,
                            uart_idle_level, uart_pin};
      4'h6: paged_status = uart_period_mask[7:0];
      4'h7: paged_status = {1'b0, uart_period_mask[14:8]};
      4'h8: paged_status = {3'b000, uart_width_mask};
      4'h9: paged_status = {3'b000, uart_parity_mask, uart_stop_mask};
      4'ha: paged_status = {6'b000000, uart_candidate_count[9:8]};
      4'hb: paged_status = uart_decoded_value[7:0];
      4'hc: paged_status = {7'b0000000, uart_decoded_value[8]};
      default: paged_status = 8'hff;
    endcase
  end
  assign dedicated_out = status_mode ? paged_status : normal_status;
  assign bidir_out = raw_protocol_out;
  assign bidir_oe = raw_protocol_oe & {8{enable && contention_drive_allow}};

  wire _unused = &{
      1'b0, evidence_count, supervisor_state, fault_reason,
      transfer_valid, transfer_request, transfer_unknown, data_a_pin,
      data_b_pin, timing_observed, activity_mask, activity_seen,
      observation_ready, async_candidate_mask, select_candidate_mask
  };

endmodule

`default_nettype wire
