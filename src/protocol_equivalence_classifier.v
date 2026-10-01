/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Merge independent inference surfaces without forcing a protocol brand name.
// Every set bit is an executable or structural interpretation still supported
// by the observation. Multiple bits are a first-class equivalence result.
module protocol_equivalence_classifier (
    input  wire       router_ready,
    input  wire [2:0] structural_classes,
    input  wire       selected_sync_valid,
    input  wire       uart_ready,
    input  wire       uart_valid,
    input  wire       shared_two_wire_ready,
    input  wire       shared_two_wire_valid,
    input  wire       generic_ready,
    input  wire [2:0] generic_classes,
    output wire       ready,
    output reg  [5:0] interpretation_mask,
    output reg  [3:0] interpretation_count,
    output wire       unique_result,
    output wire       equivalent_result,
    output wire       insufficient_result
);

  integer class_index;

  assign ready = router_ready && uart_ready && shared_two_wire_ready &&
                 generic_ready;
  assign unique_result = ready && (interpretation_count == 1);
  assign equivalent_result = ready && (interpretation_count > 1);
  assign insufficient_result = ready && (interpretation_count == 0);

  always @* begin
    interpretation_mask = 0;
    interpretation_mask[0] = structural_classes[0] && uart_valid;
    interpretation_mask[1] = structural_classes[1] && selected_sync_valid;
    interpretation_mask[2] = structural_classes[2] &&
                             shared_two_wire_valid;
    interpretation_mask[3] = generic_classes[0];
    interpretation_mask[4] = generic_classes[1];
    interpretation_mask[5] = generic_classes[2];

    interpretation_count = 0;
    for (class_index = 0; class_index < 6; class_index = class_index + 1)
      interpretation_count = interpretation_count +
                             interpretation_mask[class_index];
  end

endmodule

`default_nettype wire
