/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Protocol-neutral online framing evidence over raw pin transitions. Candidate
// classes are nonexclusive: a trace may be enclosed by a two-edge control pin,
// divided by quiet gaps, and contain equal-sized event bursts simultaneously.
module generic_event_framer #(
    parameter [7:0] GAP_CYCLES = 8'd4
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire [7:0] pin_sample,
    output reg        ready,
    output reg  [2:0] candidate_classes,
    output reg  [7:0] control_candidate_mask,
    output reg  [7:0] first_burst_events,
    output reg  [7:0] latest_burst_events,
    output reg  [3:0] burst_count,
    output wire       ambiguous,
    output wire       insufficient
);

  reg running;
  reg [7:0] previous_sample;
  reg [7:0] transition_count [0:7];
  reg [7:0] age_since_event;
  reg [7:0] current_burst_events;
  reg [7:0] completed_first_events;
  reg [3:0] completed_bursts;
  reg gap_seen;
  reg fixed_still_possible;
  reg event_seen;
  reg [7:0] first_event_mask;
  reg [7:0] last_event_mask;
  reg [7:0] changed;
  integer comb_pin_index;
  integer seq_pin_index;
  integer event_increment;
  integer class_count;

  assign ambiguous = ready && (class_count > 1);
  assign insufficient = ready && (candidate_classes == 0);

  always @* begin
    control_candidate_mask = 0;
    for (comb_pin_index = 0; comb_pin_index < 8;
         comb_pin_index = comb_pin_index + 1)
      if ((transition_count[comb_pin_index] == 2) &&
          first_event_mask[comb_pin_index] &&
          last_event_mask[comb_pin_index] &&
          ((completed_first_events + current_burst_events) > 2))
        control_candidate_mask[comb_pin_index] = 1'b1;

    first_burst_events = completed_first_events;
    latest_burst_events = current_burst_events;
    burst_count = completed_bursts +
                  ((current_burst_events != 0) ? 1'b1 : 1'b0);
    candidate_classes = 0;
    candidate_classes[0] = |control_candidate_mask;
    candidate_classes[1] = gap_seen;
    candidate_classes[2] = gap_seen && fixed_still_possible &&
                           (completed_first_events == current_burst_events) &&
                           (current_burst_events != 0);
    class_count = candidate_classes[0] + candidate_classes[1] +
                  candidate_classes[2];
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      ready <= 1'b0;
      previous_sample <= 0;
      age_since_event <= 0;
      current_burst_events <= 0;
      completed_first_events <= 0;
      completed_bursts <= 0;
      gap_seen <= 1'b0;
      fixed_still_possible <= 1'b1;
      event_seen <= 1'b0;
      first_event_mask <= 0;
      last_event_mask <= 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1)
        transition_count[seq_pin_index] <= 0;
    end else if (observe_enable && !running) begin
      running <= 1'b1;
      ready <= 1'b0;
      previous_sample <= pin_sample;
      age_since_event <= 0;
      current_burst_events <= 0;
      completed_first_events <= 0;
      completed_bursts <= 0;
      gap_seen <= 1'b0;
      fixed_still_possible <= 1'b1;
      event_seen <= 1'b0;
      first_event_mask <= 0;
      last_event_mask <= 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1)
        transition_count[seq_pin_index] <= 0;
    end else if (observe_enable && running) begin
      changed = previous_sample ^ pin_sample;
      previous_sample <= pin_sample;
      event_increment = 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1) begin
        if (changed[seq_pin_index]) begin
          event_increment = event_increment + 1;
          if (transition_count[seq_pin_index] != 8'hff)
            transition_count[seq_pin_index] <=
                transition_count[seq_pin_index] + 1'b1;
        end
      end

      if (event_increment != 0) begin
        if (!event_seen) begin
          event_seen <= 1'b1;
          first_event_mask <= changed;
        end
        last_event_mask <= changed;
        if ((age_since_event >= GAP_CYCLES) &&
            (current_burst_events != 0)) begin
          gap_seen <= 1'b1;
          if (completed_bursts == 0)
            completed_first_events <= current_burst_events;
          else if (current_burst_events != completed_first_events)
            fixed_still_possible <= 1'b0;
          if (completed_bursts != 4'hf)
            completed_bursts <= completed_bursts + 1'b1;
          current_burst_events <= event_increment;
        end else if (current_burst_events <= 8'hff - event_increment) begin
          current_burst_events <= current_burst_events + event_increment;
        end else begin
          current_burst_events <= 8'hff;
        end
        age_since_event <= 0;
      end else if (age_since_event != 8'hff) begin
        age_since_event <= age_since_event + 1'b1;
      end
    end else if (!observe_enable && running) begin
      running <= 1'b0;
      ready <= 1'b1;
    end
  end

endmodule

`default_nettype wire
