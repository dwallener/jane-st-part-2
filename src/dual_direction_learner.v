/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
`timescale 1ns / 1ps

module dual_direction_learner (
    input wire clk, input wire rst_n, input wire observe,
    input wire [7:0] data_a_word, input wire [7:0] data_b_word,
    input wire [1:0] data_a_pin, input wire [1:0] data_b_pin,
    output wire direction_resolved,
    output wire [1:0] request_pin, output wire [1:0] response_pin,
    output wire [7:0] request_mask, output wire [7:0] request_value,
    output wire [143:0] candidate_masks,
    output wire [15:0] delay_value, output wire [7:0] evidence_count
);
  wire complete_ab, complete_ba;
  wire [7:0] mask_ab, value_ab, mask_ba, value_ba;
  wire [143:0] candidates_ab, candidates_ba;
  wire [15:0] delay_ab, delay_ba;
  wire [7:0] evidence_ab, evidence_ba;
  wire unused_have_ab, unused_have_ba, unused_delay_ab, unused_delay_ba;

  template_learner ab (
      .clk(clk), .rst_n(rst_n), .observe(observe),
      .observe_request(data_a_word), .observe_response(data_b_word),
      .observe_delay(16'b0), .have_evidence(unused_have_ab),
      .request_mask(mask_ab), .request_value(value_ab),
      .candidate_masks(candidates_ab), .delay_known(unused_delay_ab),
      .delay_value(delay_ab), .evidence_count(evidence_ab),
      .model_complete(complete_ab)
  );
  template_learner ba (
      .clk(clk), .rst_n(rst_n), .observe(observe),
      .observe_request(data_b_word), .observe_response(data_a_word),
      .observe_delay(16'b0), .have_evidence(unused_have_ba),
      .request_mask(mask_ba), .request_value(value_ba),
      .candidate_masks(candidates_ba), .delay_known(unused_delay_ba),
      .delay_value(delay_ba), .evidence_count(evidence_ba),
      .model_complete(complete_ba)
  );

  assign direction_resolved = complete_ab ^ complete_ba;
  assign request_pin = complete_ab ? data_a_pin : data_b_pin;
  assign response_pin = complete_ab ? data_b_pin : data_a_pin;
  assign request_mask = complete_ab ? mask_ab : mask_ba;
  assign request_value = complete_ab ? value_ab : value_ba;
  assign candidate_masks = complete_ab ? candidates_ab : candidates_ba;
  assign delay_value = complete_ab ? delay_ab : delay_ba;
  assign evidence_count = evidence_ab;
endmodule
`default_nettype wire
