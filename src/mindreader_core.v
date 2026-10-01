/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
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
  // contradiction. Status uses ui[1], ui[3:2], and ui[6:5] as a five-bit page
  // address and suppresses every ordinary control side effect.
  wire status_mode = enable && dedicated_in[7] && !dedicated_in[4];
  wire [4:0] status_page = {dedicated_in[1], dedicated_in[3:2],
                            dedicated_in[6:5]};
  wire discover_enable = enable && !status_mode && dedicated_in[0];
  wire learn_enable = enable && !status_mode && dedicated_in[1];
  wire promote = enable && !status_mode && dedicated_in[2];
  wire ownership_granted = enable && !status_mode && dedicated_in[3];
  wire activate = enable && dedicated_in[4];
  wire revoke = dedicated_in[5] && !status_mode;
  wire clear_fault = dedicated_in[6] && !status_mode;
  wire contradiction = enable && dedicated_in[7] && dedicated_in[4];

  wire [7:0] protocol_in = bidir_in;
  wire [7:0] spi_protocol_out;
  wire [7:0] spi_protocol_oe;
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
  wire router_evidence_saturated;

  serial_hypothesis_router hypothesis_router (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(discover_enable || learn_enable),
      .pin_sample(bidir_in), .ready(router_ready),
      .activity_mask(router_activity_mask),
      .async_candidate_mask(async_candidate_mask),
      .clock_candidate_mask(clock_candidate_mask),
      .select_candidate_mask(select_candidate_mask),
      .candidate_classes(candidate_classes),
      .evidence_saturated(router_evidence_saturated),
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
  wire uart_evidence_saturated;

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
      .decoded_value(uart_decoded_value),
      .evidence_saturated(uart_evidence_saturated)
  );

  wire i2c_ready;
  wire i2c_candidate_valid;
  wire i2c_candidate_ambiguous;
  wire [5:0] i2c_candidate_count;
  wire [7:0] i2c_clock_mask;
  wire [7:0] i2c_data_mask;
  wire [2:0] i2c_clock_pin;
  wire [2:0] i2c_data_pin;
  wire [7:0] i2c_first_byte;
  wire [7:0] i2c_second_byte;
  wire [1:0] i2c_ack_bits;
  wire [1:0] i2c_byte_count;
  wire i2c_open_drain_required;
  wire i2c_evidence_saturated;

  i2c_symbol_hypothesis i2c_hypothesis (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(discover_enable || learn_enable),
      .pin_sample(bidir_in), .ready(i2c_ready),
      .candidate_valid(i2c_candidate_valid),
      .candidate_ambiguous(i2c_candidate_ambiguous),
      .candidate_count(i2c_candidate_count),
      .clock_candidate_mask(i2c_clock_mask),
      .data_candidate_mask(i2c_data_mask),
      .clock_pin(i2c_clock_pin), .data_pin(i2c_data_pin),
      .first_byte(i2c_first_byte), .second_byte(i2c_second_byte),
      .ack_bits(i2c_ack_bits), .decoded_byte_count(i2c_byte_count),
      .evidence_saturated(i2c_evidence_saturated),
      .open_drain_required(i2c_open_drain_required)
  );

  wire generic_ready;
  wire [2:0] generic_candidate_classes;
  wire [7:0] generic_control_mask;
  wire [7:0] generic_first_events;
  wire [7:0] generic_latest_events;
  wire [3:0] generic_burst_count;
  wire generic_ambiguous;
  wire generic_insufficient;
  wire generic_evidence_saturated;

  generic_event_framer generic_framer (
      .clk(clk), .rst_n(rst_n),
      .observe_enable(discover_enable || learn_enable),
      .pin_sample(bidir_in), .ready(generic_ready),
      .candidate_classes(generic_candidate_classes),
      .control_candidate_mask(generic_control_mask),
      .first_burst_events(generic_first_events),
      .latest_burst_events(generic_latest_events),
      .burst_count(generic_burst_count),
      .evidence_saturated(generic_evidence_saturated),
      .ambiguous(generic_ambiguous),
      .insufficient(generic_insufficient)
  );

  wire equivalence_ready;
  wire [5:0] interpretation_mask;
  wire [3:0] interpretation_count;
  wire interpretation_unique;
  wire interpretation_equivalent;
  wire interpretation_insufficient;

  protocol_equivalence_classifier equivalence_classifier (
      .router_ready(router_ready),
      .structural_classes(candidate_classes),
      .selected_sync_valid(physical_complete),
      .uart_ready(uart_ready), .uart_valid(uart_candidate_valid),
      .shared_two_wire_ready(i2c_ready),
      .shared_two_wire_valid(i2c_candidate_valid),
      .generic_ready(generic_ready),
      .generic_classes(generic_candidate_classes),
      .ready(equivalence_ready),
      .interpretation_mask(interpretation_mask),
      .interpretation_count(interpretation_count),
      .unique_result(interpretation_unique),
      .equivalent_result(interpretation_equivalent),
      .insufficient_result(interpretation_insufficient)
  );

  wire mismatch_now;
  wire contention_drive_allow;
  wire contention_fault;
  // mismatch_now gates the pad OE combinationally through drive_allow. Only
  // the registered fault feeds the supervisor, avoiding a combinational loop
  // through drive_enable while preserving immediate electrical release.
  wire contention = contention_fault;
  wire physical_evidence_saturated;
  wire spi_frame_incomplete;

  autonomous_spi_mindreader mindreader (
      .clk(clk), .rst_n(rst_n),
      .discover_enable(discover_enable), .learn_enable(learn_enable),
      .promote(promote), .timing_safe(timing_admissible),
      .ownership_granted(ownership_granted), .activate(activate),
      .revoke(revoke), .contradiction(contradiction),
      .contention(contention), .clear_fault(clear_fault),
      .pin_in(protocol_in), .pin_out(spi_protocol_out),
      .pin_oe(spi_protocol_oe), .physical_complete(physical_complete),
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
      .inferred_sample_trailing(sample_trailing),
      .physical_evidence_saturated(physical_evidence_saturated),
      .frame_incomplete(spi_frame_incomplete)
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
      .pin_in(protocol_in), .pin_out(spi_protocol_out),
      .pin_oe(spi_protocol_oe), .mismatch_now(mismatch_now),
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
  wire evidence_saturated = router_evidence_saturated ||
                            uart_evidence_saturated ||
                            i2c_evidence_saturated ||
                            generic_evidence_saturated ||
                            physical_evidence_saturated;
  wire [7:0] closure_mask = {
      2'b00,
      generic_candidate_classes,
      i2c_candidate_valid,
      physical_complete,
      uart_candidate_valid
  };
  wire [7:0] knowledge_state;
  wire [7:0] knowledge_reason;
  wire [7:0] next_evidence;
  wire [7:0] knowledge_safety;

  protocol_knowledge_reporter knowledge_reporter (
      .observation_active(discover_enable || learn_enable),
      .report_ready(equivalence_ready),
      .activity_seen(activity_seen), .bus_quiet(bus_quiet),
      .evidence_saturated(evidence_saturated),
      .contradiction(fault_reason == 3'd1),
      .interpretation_mask(interpretation_mask),
      .interpretation_count(interpretation_count),
      .closure_mask(closure_mask),
      .roles_resolved(physical_complete && direction_resolved),
      .timing_admissible(timing_admissible),
      .ownership_granted(ownership_granted),
      .model_ready(frozen_model_valid),
      .knowledge_state(knowledge_state), .reason_code(knowledge_reason),
      .next_evidence_code(next_evidence), .safety_status(knowledge_safety)
  );
  reg activate_previous;
  reg i2c_ready_seen;
  reg [2:0] interrogation_evidence_count;
  wire activate_rise = activate && !activate_previous;
  wire interrogation_passive_accepted = i2c_ready && !i2c_ready_seen &&
      i2c_candidate_valid && !i2c_candidate_ambiguous &&
      (i2c_byte_count != 0) && !i2c_evidence_saturated;

  always @(posedge clk) begin
    if (!rst_n) begin
      activate_previous <= 1'b0;
      i2c_ready_seen <= 1'b0;
      interrogation_evidence_count <= 0;
    end else if (clear_fault) begin
      activate_previous <= 1'b0;
      // The current ready level is stale evidence after a clear. Mark it as
      // consumed so only a new low-to-high completion can reach the learner.
      i2c_ready_seen <= i2c_ready;
      interrogation_evidence_count <= 0;
    end else begin
      activate_previous <= activate;
      if (!i2c_ready)
        i2c_ready_seen <= 1'b0;
      else
        i2c_ready_seen <= 1'b1;
      if (interrogation_passive_accepted &&
          interrogation_evidence_count != 3'd7)
        interrogation_evidence_count <= interrogation_evidence_count + 1'b1;
    end
  end

  wire [7:0] interrogation_out;
  wire [7:0] interrogation_oe;
  wire interrogation_proposal_valid;
  wire [6:0] interrogation_proposal_request;
  wire interrogation_busy;
  wire interrogation_done;
  wire interrogation_resolved;
  wire interrogation_contradiction;
  wire interrogation_timed_out;
  wire interrogation_revoked;
  wire [4:0] interrogation_candidate_count;
  wire interrogation_winner_invert;
  wire [2:0] interrogation_winner_bit;
  wire interrogation_roles_admitted = i2c_candidate_valid &&
      !i2c_candidate_ambiguous && !i2c_evidence_saturated;
  wire interrogation_eligible = (interrogation_evidence_count != 0) &&
      interrogation_roles_admitted && interrogation_proposal_valid &&
      (interrogation_candidate_count > 1) && !frozen_model_valid &&
      !interrogation_contradiction && !interrogation_timed_out &&
      !interrogation_revoked;
  wire interrogation_authorize = enable && ownership_granted &&
      interrogation_eligible && !revoke && !contradiction;
  wire interrogation_start = activate_rise && interrogation_authorize;
  wire interrogation_rst_n = rst_n && !clear_fault;

  adaptive_open_drain_interrogator adaptive_interrogator (
      .clk(clk), .rst_n(interrogation_rst_n),
      .passive_observation_valid(interrogation_passive_accepted),
      .passive_request(i2c_first_byte[7:1]),
      .passive_ack(!i2c_ack_bits[0]),
      .start(interrogation_start), .authorize(interrogation_authorize),
      .abort_request(revoke || contradiction || !enable || frozen_model_valid),
      .clock_pin(i2c_clock_pin), .data_pin(i2c_data_pin),
      .pin_in(protocol_in), .pin_out(interrogation_out),
      .pin_oe(interrogation_oe),
      .proposal_valid(interrogation_proposal_valid),
      .proposal_request(interrogation_proposal_request),
      .busy(interrogation_busy), .probe_done(interrogation_done),
      .resolved(interrogation_resolved),
      .contradiction(interrogation_contradiction),
      .timed_out(interrogation_timed_out),
      .revoked(interrogation_revoked),
      .candidate_count(interrogation_candidate_count),
      .winner_invert(interrogation_winner_invert),
      .winner_bit(interrogation_winner_bit)
  );

  wire spi_pad_owner = frozen_model_valid;
  wire [7:0] selected_protocol_out = spi_pad_owner
      ? spi_protocol_out : interrogation_out;
  wire [7:0] selected_protocol_oe = spi_pad_owner
      ? (spi_protocol_oe & {8{contention_drive_allow}}) : interrogation_oe;

  reg [7:0] paged_status;
  always @* begin
    case (status_page)
      5'h00: paged_status = router_activity_mask;
      5'h01: paged_status = quiet_age;
      5'h02: paged_status = structural_status;
      5'h03: paged_status = clock_candidate_mask;
      5'h04: paged_status = uart_candidate_count[7:0];
      5'h05: paged_status = {uart_ready, uart_candidate_valid,
                            uart_candidate_ambiguous, uart_pin_valid,
                            uart_idle_level, uart_pin};
      5'h06: paged_status = uart_period_mask[7:0];
      5'h07: paged_status = {1'b0, uart_period_mask[14:8]};
      5'h08: paged_status = {3'b000, uart_width_mask};
      5'h09: paged_status = {3'b000, uart_parity_mask, uart_stop_mask};
      5'h0a: paged_status = {6'b000000, uart_candidate_count[9:8]};
      5'h0b: paged_status = uart_decoded_value[7:0];
      5'h0c: paged_status = {7'b0000000, uart_decoded_value[8]};
      5'h0d: paged_status = {i2c_ready, i2c_candidate_valid,
                            i2c_candidate_ambiguous,
                            i2c_candidate_count[4:0]};
      5'h0e: paged_status = i2c_clock_mask;
      5'h0f: paged_status = i2c_data_mask;
      5'h10: paged_status = {generic_ready, generic_ambiguous,
                             generic_insufficient,
                             generic_burst_count[1:0],
                             generic_candidate_classes};
      5'h11: paged_status = generic_control_mask;
      5'h12: paged_status = generic_first_events;
      5'h13: paged_status = generic_latest_events;
      5'h14: paged_status = {2'b00, interpretation_mask};
      5'h15: paged_status = {equivalence_ready,
                             interpretation_equivalent,
                             interpretation_unique,
                             interpretation_insufficient,
                             interpretation_count};
      5'h16: paged_status = knowledge_state;
      5'h17: paged_status = knowledge_reason;
      5'h18: paged_status = next_evidence;
      5'h19: paged_status = knowledge_safety;
      5'h1a: paged_status = closure_mask;
      5'h1b: paged_status = {1'b0, evidence_saturated,
                             router_evidence_saturated,
                             uart_evidence_saturated,
                             i2c_evidence_saturated,
                             generic_evidence_saturated,
                             physical_evidence_saturated,
                             spi_frame_incomplete};
      5'h1c: paged_status = {interrogation_resolved,
                             interrogation_proposal_valid,
                             interrogation_busy, interrogation_done,
                             interrogation_contradiction,
                             interrogation_timed_out,
                             interrogation_revoked,
                             (interrogation_evidence_count != 0)};
      5'h1d: paged_status = {3'b000, interrogation_candidate_count};
      5'h1e: paged_status = {1'b0, interrogation_proposal_request};
      5'h1f: paged_status = {interrogation_resolved,
                             interrogation_winner_invert,
                             interrogation_winner_bit,
                             interrogation_evidence_count};
      default: paged_status = 8'hff;
    endcase
  end
  assign dedicated_out = status_mode ? paged_status : normal_status;
  assign bidir_out = selected_protocol_out;
  assign bidir_oe = selected_protocol_oe & {8{enable}};

  wire _unused = &{
      1'b0, evidence_count, supervisor_state, fault_reason,
      transfer_valid, transfer_request, transfer_unknown, data_a_pin,
      data_b_pin, timing_observed, mismatch_now, activity_mask, activity_seen,
      observation_ready, async_candidate_mask, select_candidate_mask,
      i2c_candidate_count[5], i2c_clock_pin, i2c_data_pin,
      i2c_first_byte[0], i2c_second_byte, i2c_ack_bits[1],
      i2c_open_drain_required, generic_burst_count[3:2]
  };

endmodule

`default_nettype wire
