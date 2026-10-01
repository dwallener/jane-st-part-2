/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Passive bounded inference for one anonymous four-pin, eight-bit SPI frame.
// Data direction and bit order intentionally remain outside this stage.
module spi_physical_learner (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       capture_enable,
    input  wire [3:0] pin_sample,
    output reg        ready,
    output wire       physical_complete,
    output reg  [1:0] select_pin,
    output reg  [1:0] clock_pin,
    output reg  [1:0] data_a_pin,
    output reg  [1:0] data_b_pin,
    output reg        select_active_level,
    output reg        clock_idle_level,
    output reg        sample_trailing,
    output reg  [4:0] candidate_count
);

  reg running;
  reg [3:0] initial_sample;
  reg [3:0] previous_sample;
  reg [4:0] transition_count [0:3];
  reg [15:0] clock_outside_select;
  reg [15:0] leading_data_dirty;
  reg [15:0] trailing_data_dirty;
  reg [15:0] candidate_mask;
  reg [3:0] changed;
  reg [3:0] data_mask;
  reg selected;
  integer pin_index;
  integer select_index;
  integer clock_index;
  integer pair_index;
  integer scan_index;
  integer found_data;

  assign physical_complete = ready && (candidate_count == 1);

  always @* begin
    candidate_count = 0;
    select_pin = 0;
    clock_pin = 0;
    sample_trailing = 0;
    for (scan_index = 0; scan_index < 16; scan_index = scan_index + 1) begin
      if (candidate_mask[scan_index]) begin
        candidate_count = candidate_count + 1'b1;
        select_pin = scan_index >> 2;
        clock_pin = scan_index & 3;
        sample_trailing = leading_data_dirty[scan_index];
      end
    end

    select_active_level = ~initial_sample[select_pin];
    clock_idle_level = initial_sample[clock_pin];
    data_a_pin = 0;
    data_b_pin = 0;
    found_data = 0;
    for (scan_index = 0; scan_index < 4; scan_index = scan_index + 1) begin
      if ((scan_index != select_pin) && (scan_index != clock_pin)) begin
        if (found_data == 0) begin
          data_a_pin = scan_index;
        end else begin
          data_b_pin = scan_index;
        end
        found_data = found_data + 1;
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      ready <= 1'b0;
      initial_sample <= 4'b0;
      previous_sample <= 4'b0;
      clock_outside_select <= 16'b0;
      leading_data_dirty <= 16'b0;
      trailing_data_dirty <= 16'b0;
      candidate_mask <= 16'b0;
      for (pin_index = 0; pin_index < 4; pin_index = pin_index + 1) begin
        transition_count[pin_index] <= 0;
      end
    end else if (capture_enable && !running) begin
      running <= 1'b1;
      ready <= 1'b0;
      initial_sample <= pin_sample;
      previous_sample <= pin_sample;
      clock_outside_select <= 16'b0;
      leading_data_dirty <= 16'b0;
      trailing_data_dirty <= 16'b0;
      candidate_mask <= 16'b0;
      for (pin_index = 0; pin_index < 4; pin_index = pin_index + 1) begin
        transition_count[pin_index] <= 0;
      end
    end else if (capture_enable && running) begin
      changed = previous_sample ^ pin_sample;
      previous_sample <= pin_sample;
      for (pin_index = 0; pin_index < 4; pin_index = pin_index + 1) begin
        if (changed[pin_index] && transition_count[pin_index] != 5'h1f) begin
          transition_count[pin_index] <= transition_count[pin_index] + 1'b1;
        end
      end
      for (select_index = 0; select_index < 4; select_index = select_index + 1) begin
        for (clock_index = 0; clock_index < 4; clock_index = clock_index + 1) begin
          pair_index = select_index * 4 + clock_index;
          if (select_index != clock_index && changed[clock_index]) begin
            selected = pin_sample[select_index] != initial_sample[select_index];
            if (!selected) begin
              clock_outside_select[pair_index] <= 1'b1;
            end else begin
              data_mask = 4'b1111;
              data_mask[select_index] = 1'b0;
              data_mask[clock_index] = 1'b0;
              if (previous_sample[clock_index] == initial_sample[clock_index]) begin
                if (|(changed & data_mask)) begin
                  leading_data_dirty[pair_index] <= 1'b1;
                end
              end else if (|(changed & data_mask)) begin
                trailing_data_dirty[pair_index] <= 1'b1;
              end
            end
          end
        end
      end
    end else if (!capture_enable && running) begin
      running <= 1'b0;
      ready <= 1'b1;
      for (select_index = 0; select_index < 4; select_index = select_index + 1) begin
        for (clock_index = 0; clock_index < 4; clock_index = clock_index + 1) begin
          pair_index = select_index * 4 + clock_index;
          candidate_mask[pair_index] <=
              (select_index != clock_index) &&
              (transition_count[select_index] == 2) &&
              (transition_count[clock_index] == 16) &&
              (pin_sample[select_index] == initial_sample[select_index]) &&
              (pin_sample[clock_index] == initial_sample[clock_index]) &&
              !clock_outside_select[pair_index] &&
              (leading_data_dirty[pair_index] ^
               trailing_data_dirty[pair_index]);
        end
      end
    end
  end

endmodule

`default_nettype wire
