/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

module tt_um_dwallener_mindreader (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  wire [7:0] core_dedicated_out;
  wire [7:0] core_bidir_out;
  wire [7:0] core_bidir_oe;

  mindreader_core core (
      .clk            (clk),
      .rst_n          (rst_n),
      .enable         (ena),
      .dedicated_in   (ui_in),
      .dedicated_out  (core_dedicated_out),
      .bidir_in       (uio_in),
      .bidir_out      (core_bidir_out),
      .bidir_oe       (core_bidir_oe)
  );

  // The wrapper owns Tiny Tapeout's disabled-state behavior. All substantive
  // behavior remains in the portable core.
  assign uo_out  = ena ? core_dedicated_out : 8'h00;
  assign uio_out = ena ? core_bidir_out     : 8'h00;
  assign uio_oe  = ena ? core_bidir_oe      : 8'h00;

  wire _unused = &{1'b0};

endmodule

`default_nettype wire
