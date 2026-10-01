/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Loads and executes the first 22-byte DP hierarchical model format.
// The model is written bytewise, then atomically admitted by load_commit.
module hierarchical_model_executor (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       load_valid,
    input  wire [4:0] load_address,
    input  wire [7:0] load_data,
    input  wire       load_commit,
    output reg        model_valid,
    output reg        load_error,
    input  wire       request_valid,
    input  wire [7:0] request_value,
    output wire       request_ready,
    output reg        response_valid,
    output reg  [7:0] response_value,
    output reg        unknown,
    output reg        busy,
    output wire [1:0] select_pin,
    output wire [1:0] clock_pin,
    output wire [1:0] request_pin,
    output wire [1:0] response_pin,
    output wire       select_active_level,
    output wire       clock_idle_level,
    output wire       sample_trailing,
    output wire       bit_reverse_equivalent,
    output wire [7:0] learned_request_mask,
    output wire [7:0] learned_request_value,
    output wire [39:0] learned_expressions
);

  reg [7:0] model_bytes [0:21];
  reg [15:0] delay_counter;
  reg [7:0] evaluated_response;
  reg expressions_valid;
  integer byte_index;
  integer response_bit;
  integer expression_code;

  wire [7:0] flags = model_bytes[4];
  wire [7:0] pin_map = model_bytes[5];
  wire [7:0] model_request_mask = model_bytes[13];
  wire [7:0] model_request_value = model_bytes[14];
  wire [39:0] packed_expressions = {
      model_bytes[19], model_bytes[18], model_bytes[17],
      model_bytes[16], model_bytes[15]
  };
  wire [15:0] model_delay = {model_bytes[21], model_bytes[20]};
  wire predicate_match =
      (request_value & model_request_mask) == model_request_value;

  assign select_pin = pin_map[1:0];
  assign clock_pin = pin_map[3:2];
  assign request_pin = pin_map[5:4];
  assign response_pin = pin_map[7:6];
  assign select_active_level = flags[0];
  assign clock_idle_level = flags[1];
  assign sample_trailing = flags[2];
  assign bit_reverse_equivalent = flags[3];
  assign learned_request_mask = model_request_mask;
  assign learned_request_value = model_request_value;
  assign learned_expressions = packed_expressions;
  assign request_ready = model_valid && !busy;

  always @* begin
    expressions_valid = 1'b1;
    evaluated_response = 8'b0;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      expression_code =
          (packed_expressions >> (response_bit * 5)) & 5'h1f;
      if (expression_code == 0) begin
        evaluated_response[response_bit] = 1'b0;
      end else if (expression_code == 1) begin
        evaluated_response[response_bit] = 1'b1;
      end else if (expression_code < 18) begin
        if (expression_code[0]) begin
          evaluated_response[response_bit] =
              ~request_value[(expression_code - 2) >> 1];
        end else begin
          evaluated_response[response_bit] =
              request_value[(expression_code - 2) >> 1];
        end
      end else begin
        expressions_valid = 1'b0;
      end
    end
  end

  wire distinct_pins =
      (select_pin != clock_pin) &&
      (select_pin != request_pin) &&
      (select_pin != response_pin) &&
      (clock_pin != request_pin) &&
      (clock_pin != response_pin) &&
      (request_pin != response_pin);

  wire commit_valid =
      (model_bytes[0] == 8'h44) &&
      (model_bytes[1] == 8'h50) &&
      (model_bytes[2] == 8'h01) &&
      (model_bytes[3] == 8'h01) &&
      ((flags & 8'hf0) == 0) &&
      distinct_pins &&
      (model_bytes[6] == 8'd8) &&
      (model_bytes[11] == 8'd10) &&
      (model_bytes[12] == 8'h00) &&
      ((model_request_value & ~model_request_mask) == 0) &&
      expressions_valid;

  always @(posedge clk) begin
    if (!rst_n) begin
      for (byte_index = 0; byte_index < 22; byte_index = byte_index + 1) begin
        model_bytes[byte_index] <= 8'b0;
      end
      model_valid <= 1'b0;
      load_error <= 1'b0;
      delay_counter <= 16'b0;
      response_valid <= 1'b0;
      response_value <= 8'b0;
      unknown <= 1'b0;
      busy <= 1'b0;
    end else begin
      response_valid <= 1'b0;
      unknown <= 1'b0;
      load_error <= 1'b0;

      if (load_valid && load_address < 22) begin
        model_bytes[load_address] <= load_data;
      end

      if (load_commit) begin
        model_valid <= commit_valid;
        load_error <= !commit_valid;
        busy <= 1'b0;
      end else if (busy) begin
        if (delay_counter == 16'd1) begin
          delay_counter <= 16'b0;
          response_valid <= 1'b1;
          busy <= 1'b0;
        end else begin
          delay_counter <= delay_counter - 16'd1;
        end
      end else if (request_valid) begin
        if (!model_valid || !predicate_match) begin
          unknown <= 1'b1;
        end else begin
          response_value <= evaluated_response;
          if (model_delay == 16'b0) begin
            response_valid <= 1'b1;
          end else begin
            delay_counter <= model_delay;
            busy <= 1'b1;
          end
        end
      end
    end
  end

endmodule

`default_nettype wire
