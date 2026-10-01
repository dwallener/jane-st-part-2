/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Online, passive shared-two-wire hypothesis elimination. All directed
// clock/data assignments are initially possible; each observed edge updates or
// removes candidates. The block recognizes start, rising-edge data symbols,
// nine-bit byte/ACK groups, and stop. It never controls a pad.
module i2c_symbol_hypothesis (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire [7:0] pin_sample,
    output reg        ready,
    output wire       candidate_valid,
    output wire       candidate_ambiguous,
    output reg  [5:0] candidate_count,
    output reg  [7:0] clock_candidate_mask,
    output reg  [7:0] data_candidate_mask,
    output reg  [2:0] clock_pin,
    output reg  [2:0] data_pin,
    output reg  [7:0] first_byte,
    output reg  [7:0] second_byte,
    output reg  [1:0] ack_bits,
    output reg  [1:0] decoded_byte_count,
    output wire       open_drain_required
);

  reg running;
  reg [7:0] previous_sample;
  reg [63:0] alive;
  reg [63:0] active;
  reg [63:0] start_seen;
  reg [63:0] stop_seen;
  reg [3:0] bit_position [0:63];
  reg [1:0] byte_count [0:63];
  reg [7:0] byte_shift [0:63];
  reg [7:0] candidate_first [0:63];
  reg [7:0] candidate_second [0:63];
  reg [1:0] candidate_ack [0:63];

  integer candidate_index;
  integer count_index;
  integer candidate_clock;
  integer candidate_data;
  reg is_start;
  reg is_stop;
  reg is_clock_rise;

  assign candidate_valid = ready && (candidate_count != 0);
  assign candidate_ambiguous = candidate_valid && (candidate_count != 1);
  assign open_drain_required = candidate_valid;

  // Final reporting scans only the surviving candidates. During capture the
  // same state is being pruned online on every input sample.
  always @* begin
    candidate_count = 0;
    clock_candidate_mask = 0;
    data_candidate_mask = 0;
    clock_pin = 0;
    data_pin = 0;
    first_byte = 0;
    second_byte = 0;
    ack_bits = 0;
    decoded_byte_count = 0;
    count_index = 0;
    for (count_index = 0; count_index < 64;
         count_index = count_index + 1) begin
      if (alive[count_index] && start_seen[count_index] &&
          stop_seen[count_index] && !active[count_index]) begin
        candidate_count = candidate_count + 1'b1;
        clock_candidate_mask[count_index >> 3] = 1'b1;
        data_candidate_mask[count_index & 7] = 1'b1;
        clock_pin = count_index >> 3;
        data_pin = count_index & 7;
        first_byte = candidate_first[count_index];
        second_byte = candidate_second[count_index];
        ack_bits = candidate_ack[count_index];
        decoded_byte_count = byte_count[count_index];
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      ready <= 1'b0;
      previous_sample <= 0;
      alive <= 0;
      active <= 0;
      start_seen <= 0;
      stop_seen <= 0;
      for (candidate_index = 0; candidate_index < 64;
           candidate_index = candidate_index + 1) begin
        bit_position[candidate_index] <= 0;
        byte_count[candidate_index] <= 0;
        byte_shift[candidate_index] <= 0;
        candidate_first[candidate_index] <= 0;
        candidate_second[candidate_index] <= 0;
        candidate_ack[candidate_index] <= 0;
      end
    end else if (observe_enable && !running) begin
      running <= 1'b1;
      ready <= 1'b0;
      previous_sample <= pin_sample;
      active <= 0;
      start_seen <= 0;
      stop_seen <= 0;
      for (candidate_index = 0; candidate_index < 64;
           candidate_index = candidate_index + 1) begin
        candidate_clock = candidate_index >> 3;
        candidate_data = candidate_index & 7;
        alive[candidate_index] <=
            (candidate_clock != candidate_data) &&
            pin_sample[candidate_clock] && pin_sample[candidate_data];
        bit_position[candidate_index] <= 0;
        byte_count[candidate_index] <= 0;
        byte_shift[candidate_index] <= 0;
        candidate_first[candidate_index] <= 0;
        candidate_second[candidate_index] <= 0;
        candidate_ack[candidate_index] <= 0;
      end
    end else if (observe_enable && running) begin
      previous_sample <= pin_sample;
      for (candidate_index = 0; candidate_index < 64;
           candidate_index = candidate_index + 1) begin
        candidate_clock = candidate_index >> 3;
        candidate_data = candidate_index & 7;
        is_start = previous_sample[candidate_data] &&
                   !pin_sample[candidate_data] &&
                   pin_sample[candidate_clock];
        is_stop = !previous_sample[candidate_data] &&
                  pin_sample[candidate_data] &&
                  pin_sample[candidate_clock];
        is_clock_rise = !previous_sample[candidate_clock] &&
                        pin_sample[candidate_clock];

        if (alive[candidate_index]) begin
          if (is_start) begin
            start_seen[candidate_index] <= 1'b1;
            active[candidate_index] <= 1'b1;
            stop_seen[candidate_index] <= 1'b0;
            bit_position[candidate_index] <= 0;
            byte_count[candidate_index] <= 0;
          end else if (is_stop) begin
            // A STOP raises data while clock is high. The preceding clock
            // rise may look like the first bit of another group to a purely
            // edge-driven decoder; discard that incomplete trailing group.
            if (active[candidate_index] &&
                (byte_count[candidate_index] != 0)) begin
              stop_seen[candidate_index] <= 1'b1;
              active[candidate_index] <= 1'b0;
              bit_position[candidate_index] <= 0;
            end else begin
              alive[candidate_index] <= 1'b0;
            end
          end else if (is_clock_rise && active[candidate_index]) begin
            if (bit_position[candidate_index] < 8) begin
              byte_shift[candidate_index] <=
                  {byte_shift[candidate_index][6:0],
                   pin_sample[candidate_data]};
              bit_position[candidate_index] <=
                  bit_position[candidate_index] + 1'b1;
            end else begin
              if (byte_count[candidate_index] == 0) begin
                candidate_first[candidate_index] <=
                    byte_shift[candidate_index];
                candidate_ack[candidate_index][0] <=
                    pin_sample[candidate_data];
              end else if (byte_count[candidate_index] == 1) begin
                candidate_second[candidate_index] <=
                    byte_shift[candidate_index];
                candidate_ack[candidate_index][1] <=
                    pin_sample[candidate_data];
              end
              if (byte_count[candidate_index] != 3)
                byte_count[candidate_index] <=
                    byte_count[candidate_index] + 1'b1;
              bit_position[candidate_index] <= 0;
            end
          end
        end
      end
    end else if (!observe_enable && running) begin
      running <= 1'b0;
      ready <= 1'b1;
    end
  end

endmodule

`default_nettype wire
