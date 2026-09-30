/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Portable smoke-test core. This is intentionally not the protocol-learning
// architecture; it only proves reset, clock, enable, and every TT I/O path.
module mindreader_core (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire [7:0] dedicated_in,
    output wire [7:0] dedicated_out,
    input  wire [7:0] bidir_in,
    output wire [7:0] bidir_out,
    output wire [7:0] bidir_oe
);

  reg [7:0] counter;

  always @(posedge clk) begin
    if (!rst_n) begin
      counter <= 8'h00;
    end else if (enable) begin
      counter <= counter + 8'h01;
    end
  end

  assign dedicated_out = counter ^ dedicated_in;
  assign bidir_out      = counter + bidir_in;
  assign bidir_oe       = 8'h0f;

endmodule

`default_nettype wire
