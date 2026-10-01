/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Fail-safe authority boundary between passive observation and pin driving.
module mindreader_supervisor (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       evidence_present,
    input  wire       model_complete,
    input  wire       direction_resolved,
    input  wire       stream_causal,
    input  wire       timing_safe,
    input  wire       ownership_granted,
    input  wire       activate,
    input  wire       revoke,
    input  wire       contradiction,
    input  wire       contention,
    input  wire       clear_fault,
    output reg  [2:0] state,
    output wire       passive,
    output wire       model_admitted,
    output wire       drive_enable,
    output reg  [2:0] fault_reason
);

  localparam STATE_OBSERVE   = 3'd0;
  localparam STATE_CANDIDATE = 3'd1;
  localparam STATE_ADMITTED  = 3'd2;
  localparam STATE_EMULATE   = 3'd3;
  localparam STATE_FAULT     = 3'd4;

  localparam FAULT_NONE          = 3'd0;
  localparam FAULT_CONTRADICTION = 3'd1;
  localparam FAULT_CONTENTION    = 3'd2;
  localparam FAULT_SAFETY_REVOKE = 3'd3;

  wire safety_gates =
      model_complete && direction_resolved && stream_causal && timing_safe;

  // This combinational qualification is intentional: a lost safety condition
  // disables the driver without waiting for the state register's next edge.
  assign drive_enable =
      (state == STATE_EMULATE) && safety_gates && ownership_granted &&
      !revoke && !contradiction && !contention;
  assign model_admitted = (state == STATE_ADMITTED) || (state == STATE_EMULATE);
  assign passive = !drive_enable;

  always @(posedge clk) begin
    if (!rst_n) begin
      state <= STATE_OBSERVE;
      fault_reason <= FAULT_NONE;
    end else if (state == STATE_FAULT) begin
      if (clear_fault && !contention && !contradiction) begin
        state <= STATE_OBSERVE;
        fault_reason <= FAULT_NONE;
      end
    end else if (contention) begin
      state <= STATE_FAULT;
      fault_reason <= FAULT_CONTENTION;
    end else if (contradiction) begin
      state <= STATE_FAULT;
      fault_reason <= FAULT_CONTRADICTION;
    end else begin
      case (state)
        STATE_OBSERVE: begin
          if (evidence_present) begin
            state <= STATE_CANDIDATE;
          end
        end
        STATE_CANDIDATE: begin
          if (!evidence_present) begin
            state <= STATE_OBSERVE;
          end else if (safety_gates) begin
            state <= STATE_ADMITTED;
          end
        end
        STATE_ADMITTED: begin
          if (!safety_gates) begin
            state <= STATE_CANDIDATE;
          end else if (activate && ownership_granted && !revoke) begin
            state <= STATE_EMULATE;
          end
        end
        STATE_EMULATE: begin
          if (!safety_gates) begin
            state <= STATE_FAULT;
            fault_reason <= FAULT_SAFETY_REVOKE;
          end else if (revoke || !ownership_granted) begin
            state <= STATE_ADMITTED;
          end
        end
        default: begin
          state <= STATE_FAULT;
          fault_reason <= FAULT_SAFETY_REVOKE;
        end
      endcase
    end
  end

endmodule

`default_nettype wire
