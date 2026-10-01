/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Executes one resolved template_learner model.
//
// Requests are accepted only while request_ready is high. A request outside
// the learned predicate (or an unresolved model) produces a one-cycle unknown
// pulse and is never answered. A recognized request produces a one-cycle
// response_valid pulse exactly delay_value clocks after acceptance.
module template_executor (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         request_valid,
    input  wire [7:0]   request_value_in,
    input  wire         model_complete,
    input  wire [7:0]   model_request_mask,
    input  wire [7:0]   model_request_value,
    input  wire [143:0] model_candidate_masks,
    input  wire [15:0]  model_delay_value,
    output wire         request_ready,
    output reg          response_valid,
    output reg  [7:0]   response_value,
    output reg          unknown,
    output reg          busy
);

  reg [15:0] delay_counter;
  reg [7:0] evaluated_response;
  integer response_bit;
  integer request_bit;

  wire predicate_match =
      (request_value_in & model_request_mask) == model_request_value;

  assign request_ready = !busy;

  // A complete model has exactly one asserted candidate per response slice.
  // OR form keeps the executor harmless if an invalid multi-candidate model is
  // accidentally presented; model_complete remains the admission gate.
  always @* begin
    evaluated_response = 8'b0;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      if (model_candidate_masks[response_bit * 18 + 1]) begin
        evaluated_response[response_bit] = 1'b1;
      end
      for (request_bit = 0; request_bit < 8; request_bit = request_bit + 1) begin
        if (model_candidate_masks[response_bit * 18 + 2 + request_bit * 2]) begin
          evaluated_response[response_bit] =
              evaluated_response[response_bit] | request_value_in[request_bit];
        end
        if (model_candidate_masks[response_bit * 18 + 3 + request_bit * 2]) begin
          evaluated_response[response_bit] =
              evaluated_response[response_bit] | ~request_value_in[request_bit];
        end
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      delay_counter <= 16'b0;
      response_valid <= 1'b0;
      response_value <= 8'b0;
      unknown <= 1'b0;
      busy <= 1'b0;
    end else begin
      response_valid <= 1'b0;
      unknown <= 1'b0;

      if (busy) begin
        if (delay_counter == 16'd1) begin
          delay_counter <= 16'b0;
          response_valid <= 1'b1;
          busy <= 1'b0;
        end else begin
          delay_counter <= delay_counter - 16'd1;
        end
      end else if (request_valid) begin
        if (!model_complete || !predicate_match) begin
          unknown <= 1'b1;
        end else begin
          response_value <= evaluated_response;
          if (model_delay_value == 16'b0) begin
            response_valid <= 1'b1;
          end else begin
            delay_counter <= model_delay_value;
            busy <= 1'b1;
          end
        end
      end
    end
  end

endmodule

`default_nettype wire
