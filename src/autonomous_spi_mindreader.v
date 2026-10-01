/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
`timescale 1ns / 1ps

module autonomous_spi_mindreader (
    input wire clk, input wire rst_n,
    input wire discover_enable, input wire learn_enable,
    input wire promote, input wire timing_safe,
    input wire ownership_granted, input wire activate, input wire revoke,
    input wire contradiction, input wire contention, input wire clear_fault,
    input wire [7:0] pin_in,
    output wire [7:0] pin_out, output wire [7:0] pin_oe,
    output wire physical_complete, output wire direction_resolved,
    output wire frozen_model_valid, output wire drive_enable,
    output wire [7:0] evidence_count, output wire [2:0] supervisor_state,
    output wire [2:0] fault_reason, output wire promotion_rejected,
    output wire transfer_valid, output wire [7:0] transfer_request,
    output wire transfer_unknown,
    output wire [2:0] inferred_select_pin, inferred_clock_pin,
    output wire [2:0] inferred_data_a_pin, inferred_data_b_pin,
    output wire inferred_select_active_level, inferred_clock_idle_level,
    output wire inferred_sample_trailing
);
  wire physical_ready;
  wire [2:0] select_pin, clock_pin, data_a_pin, data_b_pin;
  wire select_active_level, clock_idle_level, sample_trailing;
  wire [5:0] physical_candidates;
  wire [7:0] physical_data_mask;
  wire [3:0] physical_data_candidates;
  spi_physical_learner physical (
      .clk(clk), .rst_n(rst_n), .capture_enable(discover_enable),
      .pin_sample(pin_in), .ready(physical_ready),
      .physical_complete(physical_complete), .select_pin(select_pin),
      .clock_pin(clock_pin), .data_a_pin(data_a_pin), .data_b_pin(data_b_pin),
      .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level), .sample_trailing(sample_trailing),
      .candidate_count(physical_candidates),
      .data_candidate_mask(physical_data_mask),
      .data_candidate_count(physical_data_candidates)
  );

  wire observation_valid, observation_aborted;
  wire [7:0] data_a_word, data_b_word;
  spi_transaction_decoder decoder (
      .clk(clk), .rst_n(rst_n), .enable(learn_enable && physical_complete),
      .pin_sample(pin_in), .select_pin(select_pin), .clock_pin(clock_pin),
      .data_a_pin(data_a_pin), .data_b_pin(data_b_pin),
      .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level), .sample_trailing(sample_trailing),
      .transaction_valid(observation_valid),
      .transaction_aborted(observation_aborted),
      .data_a_word(data_a_word), .data_b_word(data_b_word)
  );

  wire [2:0] live_request_pin, live_response_pin;
  wire [7:0] live_request_mask, live_request_value;
  wire [143:0] live_candidate_masks;
  wire [15:0] live_delay;
  dual_direction_learner behavior (
      .clk(clk), .rst_n(rst_n), .observe(observation_valid),
      .data_a_word(data_a_word), .data_b_word(data_b_word),
      .data_a_pin(data_a_pin), .data_b_pin(data_b_pin),
      .direction_resolved(direction_resolved),
      .request_pin(live_request_pin), .response_pin(live_response_pin),
      .request_mask(live_request_mask), .request_value(live_request_value),
      .candidate_masks(live_candidate_masks), .delay_value(live_delay),
      .evidence_count(evidence_count)
  );

  wire live_stream_causal;
  wire [2:0] frozen_request_pin, frozen_response_pin;
  wire [7:0] frozen_request_mask, frozen_request_value;
  wire [143:0] frozen_candidate_masks;
  learned_model_promoter promoter (
      .clk(clk), .rst_n(rst_n), .promote(promote),
      .invalidate(contradiction || contention),
      .direction_resolved(direction_resolved), .timing_safe(timing_safe),
      .ownership_authorized(ownership_granted),
      .live_request_pin(live_request_pin), .live_response_pin(live_response_pin),
      .live_request_mask(live_request_mask),
      .live_request_value(live_request_value),
      .live_candidate_masks(live_candidate_masks),
      .frozen_valid(frozen_model_valid),
      .promotion_rejected(promotion_rejected),
      .live_stream_causal(live_stream_causal),
      .frozen_request_pin(frozen_request_pin),
      .frozen_response_pin(frozen_response_pin),
      .frozen_request_mask(frozen_request_mask),
      .frozen_request_value(frozen_request_value),
      .frozen_candidate_masks(frozen_candidate_masks)
  );

  wire passive, model_admitted;
  mindreader_supervisor supervisor (
      .clk(clk), .rst_n(rst_n), .evidence_present(evidence_count != 0),
      .model_complete(frozen_model_valid),
      .direction_resolved(frozen_model_valid),
      .stream_causal(frozen_model_valid), .timing_safe(timing_safe),
      .ownership_granted(ownership_granted), .activate(activate),
      .revoke(revoke), .contradiction(contradiction),
      .contention(contention), .clear_fault(clear_fault),
      .state(supervisor_state), .passive(passive),
      .model_admitted(model_admitted), .drive_enable(drive_enable),
      .fault_reason(fault_reason)
  );

  template_spi_peripheral executor (
      .clk(clk), .rst_n(rst_n), .drive_enable(drive_enable), .pin_in(pin_in),
      .select_pin(select_pin), .clock_pin(clock_pin),
      .request_pin(frozen_request_pin), .response_pin(frozen_response_pin),
      .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level), .sample_trailing(sample_trailing),
      .request_mask(frozen_request_mask),
      .request_value(frozen_request_value),
      .candidate_masks(frozen_candidate_masks), .pin_out(pin_out), .pin_oe(pin_oe),
      .transfer_valid(transfer_valid), .transfer_request(transfer_request),
      .transfer_unknown(transfer_unknown)
  );

  assign inferred_select_pin = select_pin;
  assign inferred_clock_pin = clock_pin;
  assign inferred_data_a_pin = data_a_pin;
  assign inferred_data_b_pin = data_b_pin;
  assign inferred_select_active_level = select_active_level;
  assign inferred_clock_idle_level = clock_idle_level;
  assign inferred_sample_trailing = sample_trailing;
  wire _unused_physical = &{1'b0, physical_ready, physical_candidates,
                            physical_data_mask, physical_data_candidates,
                            observation_aborted, live_delay, passive,
                            model_admitted};
endmodule
`default_nettype wire
