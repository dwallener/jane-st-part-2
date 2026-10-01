/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Always-passive evidence collector for an anonymous eight-pin connection.
// It deliberately has no output-data or output-enable ports.
module passive_bus_profiler #(
    parameter [15:0] QUIET_CYCLES = 16'd64
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire [7:0] pin_sample,
    output reg  [7:0] activity_mask,
    output wire       activity_seen,
    output wire       observation_ready,
    output wire       bus_quiet
);

  reg [7:0] previous_sample;
  reg [15:0] stable_cycles;
  reg initialized;

  wire [7:0] changed = pin_sample ^ previous_sample;
  wire any_change = |changed;

  assign activity_seen = |activity_mask;
  assign observation_ready = initialized;
  assign bus_quiet = initialized && (stable_cycles >= QUIET_CYCLES);

  always @(posedge clk) begin
    if (!rst_n) begin
      previous_sample <= 8'h00;
      stable_cycles <= 16'h0000;
      activity_mask <= 8'h00;
      initialized <= 1'b0;
    end else if (observe_enable) begin
      if (!initialized) begin
        previous_sample <= pin_sample;
        stable_cycles <= 16'h0000;
        initialized <= 1'b1;
      end else begin
        previous_sample <= pin_sample;
        activity_mask <= activity_mask | changed;
        if (any_change)
          stable_cycles <= 16'h0000;
        else if (stable_cycles < QUIET_CYCLES)
          stable_cycles <= stable_cycles + 1'b1;
      end
    end
  end

endmodule

`default_nettype wire
