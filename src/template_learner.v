/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Streaming learner for one bounded request/response context.
//
// Candidate packing for each 18-bit response slice:
//   0: constant 0
//   1: constant 1
//   2 + 2*i: copy request bit i
//   3 + 2*i: invert request bit i
module template_learner (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         observe,
    input  wire [7:0]   observe_request,
    input  wire [7:0]   observe_response,
    input  wire [15:0]  observe_delay,
    output reg          have_evidence,
    output reg  [7:0]   request_mask,
    output reg  [7:0]   request_value,
    output reg  [143:0] candidate_masks,
    output reg          delay_known,
    output reg  [15:0]  delay_value,
    output reg  [7:0]   evidence_count,
    output reg          model_complete
);

  reg [143:0] raw_candidate_masks;
  reg [143:0] observation_matches;
  integer response_bit;
  integer request_bit;

  function is_onehot18;
    input [17:0] value;
    begin
      is_onehot18 = (value != 18'b0) &&
                    ((value & (value - 18'b1)) == 18'b0);
    end
  endfunction

  // Evaluate every expression against the observation in parallel.
  always @* begin
    observation_matches = 144'b0;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      observation_matches[response_bit * 18 + 0] =
          (observe_response[response_bit] == 1'b0);
      observation_matches[response_bit * 18 + 1] =
          (observe_response[response_bit] == 1'b1);
      for (request_bit = 0; request_bit < 8; request_bit = request_bit + 1) begin
        observation_matches[response_bit * 18 + 2 + request_bit * 2] =
            (observe_response[response_bit] == observe_request[request_bit]);
        observation_matches[response_bit * 18 + 3 + request_bit * 2] =
            (observe_response[response_bit] != observe_request[request_bit]);
      end
    end
  end

  // Stable request bits are predicate bits, not response-field candidates.
  always @* begin
    candidate_masks = raw_candidate_masks;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      for (request_bit = 0; request_bit < 8; request_bit = request_bit + 1) begin
        if (request_mask[request_bit]) begin
          candidate_masks[response_bit * 18 + 2 + request_bit * 2] = 1'b0;
          candidate_masks[response_bit * 18 + 3 + request_bit * 2] = 1'b0;
        end
      end
    end
  end

  always @* begin
    model_complete = have_evidence && delay_known;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      if (!is_onehot18(candidate_masks[response_bit * 18 +: 18])) begin
        model_complete = 1'b0;
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      have_evidence       <= 1'b0;
      request_mask        <= 8'b0;
      request_value       <= 8'b0;
      raw_candidate_masks <= 144'b0;
      delay_known         <= 1'b0;
      delay_value         <= 16'b0;
      evidence_count      <= 8'b0;
    end else if (observe) begin
      if (!have_evidence) begin
        have_evidence       <= 1'b1;
        request_mask        <= 8'hff;
        request_value       <= observe_request;
        raw_candidate_masks <= observation_matches;
        delay_known         <= 1'b1;
        delay_value         <= observe_delay;
        evidence_count      <= 8'd1;
      end else begin
        request_mask  <= request_mask & ~(request_value ^ observe_request);
        request_value <= request_value &
                         (request_mask & ~(request_value ^ observe_request));
        raw_candidate_masks <= raw_candidate_masks & observation_matches;
        if (delay_value != observe_delay) begin
          delay_known <= 1'b0;
        end
        if (evidence_count != 8'hff) begin
          evidence_count <= evidence_count + 8'd1;
        end
      end
    end
  end

endmodule

`default_nettype wire
