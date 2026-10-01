/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
`timescale 1ns / 1ps

module learned_model_promoter (
    input wire clk, input wire rst_n, input wire promote, input wire invalidate,
    input wire direction_resolved, input wire timing_safe,
    input wire ownership_authorized,
    input wire [2:0] live_request_pin, input wire [2:0] live_response_pin,
    input wire [7:0] live_request_mask, input wire [7:0] live_request_value,
    input wire [143:0] live_candidate_masks,
    output reg frozen_valid, output reg promotion_rejected,
    output wire live_stream_causal,
    output reg [2:0] frozen_request_pin, output reg [2:0] frozen_response_pin,
    output reg [7:0] frozen_request_mask, output reg [7:0] frozen_request_value,
    output reg [143:0] frozen_candidate_masks
);
  reg causal;
  integer response_bit, expression_index, selected_code, selected_count;
  always @* begin
    causal = 1;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      selected_code = 0;
      selected_count = 0;
      for (expression_index = 0; expression_index < 18;
           expression_index = expression_index + 1) begin
        if (live_candidate_masks[response_bit * 18 + expression_index]) begin
          selected_code = expression_index;
          selected_count = selected_count + 1;
        end
      end
      if (selected_count != 1) causal = 0;
      if (selected_code >= 2 && ((selected_code - 2) >> 1) < response_bit)
        causal = 0;
    end
  end
  assign live_stream_causal = direction_resolved && causal;

  always @(posedge clk) begin
    if (!rst_n) begin
      frozen_valid <= 0;
      promotion_rejected <= 0;
      frozen_request_pin <= 0;
      frozen_response_pin <= 0;
      frozen_request_mask <= 0;
      frozen_request_value <= 0;
      frozen_candidate_masks <= 0;
    end else begin
      promotion_rejected <= 0;
      if (invalidate) begin
        frozen_valid <= 0;
      end else if (promote) begin
        if (direction_resolved && causal && timing_safe && ownership_authorized) begin
          frozen_valid <= 1;
          frozen_request_pin <= live_request_pin;
          frozen_response_pin <= live_response_pin;
          frozen_request_mask <= live_request_mask;
          frozen_request_value <= live_request_value;
          frozen_candidate_masks <= live_candidate_masks;
        end else begin
          promotion_rejected <= 1;
        end
      end
    end
  end
endmodule
`default_nettype wire
