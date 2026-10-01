/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Turn inference results into a compact, machine-readable account of what is
// known, why inference stopped, and which evidence should be sought next.
// This block is advisory only: it has no connection to protocol-pin outputs.
module protocol_knowledge_reporter (
    input  wire       observation_active,
    input  wire       report_ready,
    input  wire       activity_seen,
    input  wire       bus_quiet,
    input  wire       evidence_saturated,
    input  wire       contradiction,
    input  wire [5:0] interpretation_mask,
    input  wire [3:0] interpretation_count,
    input  wire [7:0] closure_mask,
    input  wire       roles_resolved,
    input  wire       timing_admissible,
    input  wire       ownership_granted,
    input  wire       model_ready,
    output reg  [7:0] knowledge_state,
    output reg  [7:0] reason_code,
    output reg  [7:0] next_evidence_code,
    output wire [7:0] safety_status
);

  localparam KNOW_OBSERVING     = 8'h00;
  localparam KNOW_CONCLUSION    = 8'h01;
  localparam KNOW_AMBIGUOUS     = 8'h02;
  localparam KNOW_INSUFFICIENT  = 8'h03;
  localparam KNOW_UNSUPPORTED   = 8'h04;
  localparam KNOW_CONTRADICTORY = 8'h05;
  localparam KNOW_COMPROMISED   = 8'h06;

  localparam REASON_NONE          = 8'h00;
  localparam REASON_IN_PROGRESS   = 8'h01;
  localparam REASON_QUIET         = 8'h02;
  localparam REASON_OPEN_BOUNDARY = 8'h03;
  localparam REASON_MULTIPLE      = 8'h04;
  localparam REASON_NO_MODEL      = 8'h05;
  localparam REASON_SATURATED     = 8'h06;
  localparam REASON_CONTRADICTION = 8'h07;

  localparam NEXT_NONE              = 8'h00;
  localparam NEXT_CONTINUE_PASSIVE  = 8'h01;
  localparam NEXT_OBSERVE_BOUNDARY  = 8'h02;
  localparam NEXT_DIFFERENTIATING   = 8'h03;
  localparam NEXT_VERIFY_ELECTRICAL = 8'h04;
  localparam NEXT_REQUEST_AUTH      = 8'h05;
  localparam NEXT_RECAPTURE         = 8'h06;
  localparam NEXT_REVIEW_UNSUPPORTED = 8'h07;

  wire candidate_closed = |closure_mask;
  wire passive_next = (next_evidence_code == NEXT_CONTINUE_PASSIVE) ||
                      (next_evidence_code == NEXT_OBSERVE_BOUNDARY) ||
                      (next_evidence_code == NEXT_DIFFERENTIATING) ||
                      (next_evidence_code == NEXT_RECAPTURE) ||
                      (next_evidence_code == NEXT_REVIEW_UNSUPPORTED);
  wire active_admissible = model_ready && roles_resolved &&
                           timing_admissible && ownership_granted &&
                           !evidence_saturated && !contradiction;

  // [7] recommendation is passive, [6] active action is prohibited,
  // [5] roles resolved, [4] timing admissible, [3] ownership granted,
  // [2] executable model ready, [1] candidate-relative closure exists,
  // [0] every currently implemented active-admission gate passes.
  assign safety_status = {
      passive_next,
      !active_admissible,
      roles_resolved,
      timing_admissible,
      ownership_granted,
      model_ready,
      candidate_closed,
      active_admissible
  };

  always @* begin
    knowledge_state = KNOW_OBSERVING;
    reason_code = REASON_IN_PROGRESS;
    next_evidence_code = NEXT_CONTINUE_PASSIVE;

    if (evidence_saturated) begin
      knowledge_state = KNOW_COMPROMISED;
      reason_code = REASON_SATURATED;
      next_evidence_code = NEXT_RECAPTURE;
    end else if (contradiction) begin
      knowledge_state = KNOW_CONTRADICTORY;
      reason_code = REASON_CONTRADICTION;
      next_evidence_code = NEXT_CONTINUE_PASSIVE;
    end else if (!observation_active && report_ready) begin
      if (interpretation_count == 0) begin
        if (!activity_seen && bus_quiet) begin
          knowledge_state = KNOW_INSUFFICIENT;
          reason_code = REASON_QUIET;
          next_evidence_code = NEXT_CONTINUE_PASSIVE;
        end else if (!candidate_closed) begin
          knowledge_state = KNOW_INSUFFICIENT;
          reason_code = REASON_OPEN_BOUNDARY;
          next_evidence_code = NEXT_OBSERVE_BOUNDARY;
        end else begin
          knowledge_state = KNOW_UNSUPPORTED;
          reason_code = REASON_NO_MODEL;
          next_evidence_code = NEXT_REVIEW_UNSUPPORTED;
        end
      end else if (interpretation_count > 1) begin
        knowledge_state = KNOW_AMBIGUOUS;
        reason_code = REASON_MULTIPLE;
        next_evidence_code = NEXT_DIFFERENTIATING;
      end else if (!candidate_closed) begin
        knowledge_state = KNOW_INSUFFICIENT;
        reason_code = REASON_OPEN_BOUNDARY;
        next_evidence_code = NEXT_OBSERVE_BOUNDARY;
      end else begin
        knowledge_state = KNOW_CONCLUSION;
        reason_code = REASON_NONE;
        if (!roles_resolved || !timing_admissible)
          next_evidence_code = NEXT_VERIFY_ELECTRICAL;
        else if (!ownership_granted)
          next_evidence_code = NEXT_REQUEST_AUTH;
        else
          next_evidence_code = NEXT_NONE;
      end
    end
  end

  wire _unused = &{1'b0, interpretation_mask};

endmodule

`default_nettype wire
