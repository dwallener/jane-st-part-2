/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
// Connect the ordinary passive shared-two-wire decoder to the adaptive
// invented-protocol learner. Only uniquely decoded, complete observations may
// become evidence. Active traffic remains separately authorization-gated.
module adaptive_i2c_interrogation_bridge (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire       start,
    input  wire       authorize,
    input  wire       abort_request,
    input  wire [7:0] pin_in,
    output wire [7:0] pin_out,
    output wire [7:0] pin_oe,
    output wire       passive_ready,
    output wire       passive_accepted,
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
    output wire [2:0] winner_bit,
    output wire [2:0] inferred_clock_pin,
    output wire [2:0] inferred_data_pin
);

  wire i2c_valid;
  wire i2c_ambiguous;
  wire [5:0] i2c_candidate_count;
  wire [7:0] i2c_clock_mask;
  wire [7:0] i2c_data_mask;
  wire [7:0] first_byte;
  wire [7:0] second_byte;
  wire [1:0] ack_bits;
  wire [1:0] decoded_byte_count;
  wire evidence_saturated;
  wire open_drain_required;
  reg ready_seen;

  assign passive_accepted = passive_ready && !ready_seen && i2c_valid &&
                            !i2c_ambiguous &&
                            (decoded_byte_count != 0) &&
                            !evidence_saturated;

  always @(posedge clk) begin
    if (!rst_n)
      ready_seen <= 1'b0;
    else if (!passive_ready)
      ready_seen <= 1'b0;
    else
      ready_seen <= 1'b1;
  end

  i2c_symbol_hypothesis passive_decoder (
      .clk(clk), .rst_n(rst_n), .observe_enable(observe_enable),
      .pin_sample(pin_in), .ready(passive_ready),
      .candidate_valid(i2c_valid), .candidate_ambiguous(i2c_ambiguous),
      .candidate_count(i2c_candidate_count),
      .clock_candidate_mask(i2c_clock_mask),
      .data_candidate_mask(i2c_data_mask),
      .clock_pin(inferred_clock_pin), .data_pin(inferred_data_pin),
      .first_byte(first_byte), .second_byte(second_byte),
      .ack_bits(ack_bits), .decoded_byte_count(decoded_byte_count),
      .evidence_saturated(evidence_saturated),
      .open_drain_required(open_drain_required)
  );

  adaptive_open_drain_interrogator interrogator (
      .clk(clk), .rst_n(rst_n),
      .passive_observation_valid(passive_accepted),
      .passive_request(first_byte[7:1]), .passive_ack(!ack_bits[0]),
      .start(start), .authorize(authorize), .abort_request(abort_request),
      .clock_pin(inferred_clock_pin), .data_pin(inferred_data_pin),
      .pin_in(pin_in), .pin_out(pin_out), .pin_oe(pin_oe),
      .proposal_valid(proposal_valid), .proposal_request(proposal_request),
      .busy(busy), .probe_done(probe_done), .resolved(resolved),
      .contradiction(contradiction), .timed_out(timed_out),
      .revoked(revoked), .candidate_count(candidate_count),
      .winner_invert(winner_invert), .winner_bit(winner_bit)
  );

  wire _unused = &{1'b0, i2c_candidate_count, i2c_clock_mask,
                    i2c_data_mask, first_byte[0], second_byte, ack_bits[1],
                    open_drain_required};
endmodule
`default_nettype wire
