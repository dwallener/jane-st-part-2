/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Family-neutral routing hints from one bounded eight-pin observation window.
// Candidate classes are deliberately nonexclusive and never grant pin drive.
module serial_hypothesis_router #(
    parameter [7:0] MIN_CLOCK_EDGES = 8'd8
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire [7:0] pin_sample,
    output reg        ready,
    output reg  [7:0] activity_mask,
    output reg  [7:0] async_candidate_mask,
    output reg  [7:0] clock_candidate_mask,
    output reg  [7:0] select_candidate_mask,
    output reg  [2:0] candidate_classes,
    output wire       insufficient,
    output wire       ambiguous
);

  reg running;
  reg [7:0] previous_sample;
  reg [7:0] rising_seen;
  reg [7:0] falling_seen;
  reg [7:0] transition_count [0:7];
  reg [7:0] changed;
  integer comb_pin_index;
  integer seq_pin_index;
  integer active_count;
  integer class_count;

  assign insufficient = ready && (candidate_classes == 3'b000);
  assign ambiguous = ready && (class_count > 1);

  always @* begin
    activity_mask = rising_seen | falling_seen;
    async_candidate_mask = rising_seen & falling_seen;
    clock_candidate_mask = 0;
    select_candidate_mask = 0;
    active_count = 0;
    for (comb_pin_index = 0; comb_pin_index < 8;
         comb_pin_index = comb_pin_index + 1) begin
      if (activity_mask[comb_pin_index])
        active_count = active_count + 1;
      if (async_candidate_mask[comb_pin_index] &&
          transition_count[comb_pin_index] >= MIN_CLOCK_EDGES)
        clock_candidate_mask[comb_pin_index] = 1'b1;
      if (async_candidate_mask[comb_pin_index] &&
          transition_count[comb_pin_index] == 2)
        select_candidate_mask[comb_pin_index] = 1'b1;
    end

    candidate_classes = 0;
    candidate_classes[0] = |async_candidate_mask;
    candidate_classes[1] = (active_count >= 4) &&
                           (|clock_candidate_mask) &&
                           (|select_candidate_mask);
    candidate_classes[2] = (active_count == 2) &&
                           (|clock_candidate_mask);

    class_count = candidate_classes[0] + candidate_classes[1] +
                  candidate_classes[2];
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      ready <= 1'b0;
      previous_sample <= 0;
      rising_seen <= 0;
      falling_seen <= 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1)
        transition_count[seq_pin_index] <= 0;
    end else if (observe_enable && !running) begin
      running <= 1'b1;
      ready <= 1'b0;
      previous_sample <= pin_sample;
      rising_seen <= 0;
      falling_seen <= 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1)
        transition_count[seq_pin_index] <= 0;
    end else if (observe_enable && running) begin
      changed = previous_sample ^ pin_sample;
      previous_sample <= pin_sample;
      rising_seen <= rising_seen | (changed & pin_sample);
      falling_seen <= falling_seen | (changed & ~pin_sample);
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1) begin
        if (changed[seq_pin_index] &&
            transition_count[seq_pin_index] != 8'hff)
          transition_count[seq_pin_index] <=
              transition_count[seq_pin_index] + 1'b1;
      end
    end else if (!observe_enable && running) begin
      running <= 1'b0;
      ready <= 1'b1;
    end
  end

endmodule

`default_nettype wire
