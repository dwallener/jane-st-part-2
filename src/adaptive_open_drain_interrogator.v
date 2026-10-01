/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
// Closed-loop invented-protocol demonstrator. Passive decoded observations and
// active wire responses update the same candidate set.
module adaptive_open_drain_interrogator (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       passive_observation_valid,
    input  wire [6:0] passive_request,
    input  wire       passive_ack,
    input  wire       start,
    input  wire       authorize,
    input  wire       abort_request,
    input  wire [2:0] clock_pin,
    input  wire [2:0] data_pin,
    input  wire [7:0] pin_in,
    output wire [7:0] pin_out,
    output wire [7:0] pin_oe,
    output wire       proposal_valid,
    output wire [6:0] proposal_request,
    output wire       busy,
    output wire       probe_done,
    output wire       resolved,
    output wire       contradiction,
    output wire       timed_out,
    output wire       revoked,
    output wire [4:0] candidate_count,
    output wire       winner_invert,
    output wire [2:0] winner_bit
);

  wire probe_acknowledged;
  wire [13:0] candidate_mask;
  wire active_observation_valid = probe_done && !timed_out && !revoked;
  wire learner_observe = passive_observation_valid || active_observation_valid;
  wire [6:0] learner_request = active_observation_valid
      ? proposal_request : passive_request;
  wire learner_ack = active_observation_valid
      ? probe_acknowledged : passive_ack;

  open_drain_bit_learner learner (
      .clk(clk), .rst_n(rst_n), .observe_valid(learner_observe),
      .observed_request(learner_request), .observed_ack(learner_ack),
      .candidate_mask(candidate_mask), .candidate_count(candidate_count),
      .proposal_valid(proposal_valid), .proposal_request(proposal_request),
      .resolved(resolved), .winner_invert(winner_invert),
      .winner_bit(winner_bit)
  );

  open_drain_address_probe probe (
      .clk(clk), .rst_n(rst_n), .start(start && proposal_valid),
      .authorize(authorize), .abort_request(abort_request),
      .clock_pin(clock_pin), .data_pin(data_pin),
      .address(proposal_request), .pin_in(pin_in),
      .pin_out(pin_out), .pin_oe(pin_oe), .busy(busy), .done(probe_done),
      .acknowledged(probe_acknowledged), .timed_out(timed_out),
      .revoked(revoked)
  );

  assign contradiction = candidate_count == 0;
  wire _unused = &{1'b0, candidate_mask};
endmodule
`default_nettype wire
