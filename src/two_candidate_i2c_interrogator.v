/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Bounded first interrogation: two candidates disagree about whether the
// target will ACK candidate_a. Both candidates are visible; target identity is
// not. ACK retains A, NACK retains B. The electrical probe is low-or-release.
module two_candidate_i2c_interrogator (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire       authorize,
    input  wire       abort_request,
    input  wire       candidates_valid,
    input  wire [6:0] candidate_a,
    input  wire [6:0] candidate_b,
    input  wire [2:0] clock_pin,
    input  wire [2:0] data_pin,
    input  wire [7:0] pin_in,
    output wire [7:0] pin_out,
    output wire [7:0] pin_oe,
    output wire       probe_valid,
    output wire [6:0] probe_address,
    output wire       busy,
    output wire       done,
    output wire       resolved,
    output wire       candidate_a_survives,
    output wire       candidate_b_survives,
    output wire       contradiction,
    output wire       timed_out,
    output wire       revoked
);

  wire query_done;
  wire acknowledged;
  wire candidates_distinct = candidate_a != candidate_b;

  assign probe_valid = candidates_valid && candidates_distinct;
  assign probe_address = candidate_a;
  assign done = query_done;
  assign resolved = query_done && !timed_out && !revoked && probe_valid;
  assign candidate_a_survives = resolved && acknowledged;
  assign candidate_b_survives = resolved && !acknowledged;
  assign contradiction = query_done && !timed_out && !revoked &&
                         !probe_valid;

  open_drain_address_probe probe (
      .clk(clk), .rst_n(rst_n),
      .start(start && probe_valid), .authorize(authorize),
      .abort_request(abort_request),
      .clock_pin(clock_pin), .data_pin(data_pin), .address(candidate_a),
      .pin_in(pin_in), .pin_out(pin_out), .pin_oe(pin_oe), .busy(busy),
      .done(query_done), .acknowledged(acknowledged),
      .timed_out(timed_out), .revoked(revoked)
  );

endmodule

`default_nettype wire
