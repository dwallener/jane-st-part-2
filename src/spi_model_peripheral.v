/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Wire-facing executor for stream-causal, eight-bit SPI models.
//
// Four anonymous pins are remapped by the loaded model.  The external SPI
// clock is oversampled by clk for edge bookkeeping; same-symbol COPY/INVERT
// expressions use a combinational request-pin-to-response-pin path.
module spi_model_peripheral (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       load_valid,
    input  wire [4:0] load_address,
    input  wire [7:0] load_data,
    input  wire       load_commit,
    output wire       model_valid,
    output wire       load_error,
    input  wire [3:0] pin_in,
    output reg  [3:0] pin_out,
    output reg  [3:0] pin_oe,
    output wire       stream_causal,
    output reg        transfer_valid,
    output reg  [7:0] transfer_request,
    output reg        transfer_unknown
);

  wire unused_request_ready;
  wire unused_response_valid;
  wire [7:0] unused_response_value;
  wire unused_unknown;
  wire unused_busy;
  wire [1:0] select_pin;
  wire [1:0] clock_pin;
  wire [1:0] request_pin;
  wire [1:0] response_pin;
  wire select_active_level;
  wire clock_idle_level;
  wire sample_trailing;
  wire unused_bit_reverse_equivalent;
  wire [7:0] request_mask;
  wire [7:0] request_value;
  wire [39:0] expressions;

  reg [3:0] previous_pins;
  reg [2:0] bit_count;
  reg [7:0] request_shift;
  reg [7:0] request_live;
  reg causal_expressions;
  reg response_bit_value;
  integer response_bit;
  integer causal_expression_code;
  integer causal_dependency_bit;
  integer live_expression_code;
  integer live_dependency_bit;
  integer current_response_bit;

  hierarchical_model_executor model (
      .clk(clk), .rst_n(rst_n),
      .load_valid(load_valid), .load_address(load_address),
      .load_data(load_data), .load_commit(load_commit),
      .model_valid(model_valid), .load_error(load_error),
      .request_valid(1'b0), .request_value(8'b0),
      .request_ready(unused_request_ready),
      .response_valid(unused_response_valid),
      .response_value(unused_response_value),
      .unknown(unused_unknown), .busy(unused_busy),
      .select_pin(select_pin), .clock_pin(clock_pin),
      .request_pin(request_pin), .response_pin(response_pin),
      .select_active_level(select_active_level),
      .clock_idle_level(clock_idle_level),
      .sample_trailing(sample_trailing),
      .bit_reverse_equivalent(unused_bit_reverse_equivalent),
      .learned_request_mask(request_mask),
      .learned_request_value(request_value),
      .learned_expressions(expressions)
  );

  wire selected = pin_in[select_pin] == select_active_level;
  wire previously_selected =
      previous_pins[select_pin] == select_active_level;
  wire leading_edge =
      (previous_pins[clock_pin] == clock_idle_level) &&
      (pin_in[clock_pin] != clock_idle_level);
  wire trailing_edge =
      (previous_pins[clock_pin] != clock_idle_level) &&
      (pin_in[clock_pin] == clock_idle_level);
  wire sampling_event =
      selected && (sample_trailing ? trailing_edge : leading_edge);

  // Canonical model words are MSB-first.  A response bit is stream-causal
  // when its request dependency is the same bit or an earlier wire-time bit.
  always @* begin
    causal_expressions = 1'b1;
    causal_dependency_bit = 0;
    for (response_bit = 0; response_bit < 8; response_bit = response_bit + 1) begin
      causal_expression_code =
          (expressions >> (response_bit * 5)) & 5'h1f;
      if (causal_expression_code >= 2) begin
        causal_dependency_bit = (causal_expression_code - 2) >> 1;
        if (causal_dependency_bit < response_bit) begin
          causal_expressions = 1'b0;
        end
      end
    end
  end

  assign stream_causal = model_valid && causal_expressions;

  // Overlay the live request pin onto the accumulated prefix.  This creates
  // the intentional same-symbol combinational path when the expression needs
  // the bit currently on the wire.
  always @* begin
    request_live = request_shift;
    current_response_bit = 7 - bit_count;
    request_live[current_response_bit] = pin_in[request_pin];
    live_expression_code =
        (expressions >> (current_response_bit * 5)) & 5'h1f;
    live_dependency_bit = 0;
    if (live_expression_code == 0) begin
      response_bit_value = 1'b0;
    end else if (live_expression_code == 1) begin
      response_bit_value = 1'b1;
    end else begin
      live_dependency_bit = (live_expression_code - 2) >> 1;
      response_bit_value = request_live[live_dependency_bit];
      if (live_expression_code[0]) begin
        response_bit_value = ~response_bit_value;
      end
    end

    pin_out = 4'b0;
    pin_oe = 4'b0;
    if (stream_causal && selected) begin
      pin_out[response_pin] = response_bit_value;
      pin_oe[response_pin] = 1'b1;
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      previous_pins <= 4'b0;
      bit_count <= 3'b0;
      request_shift <= 8'b0;
      transfer_valid <= 1'b0;
      transfer_request <= 8'b0;
      transfer_unknown <= 1'b0;
    end else begin
      previous_pins <= pin_in;
      transfer_valid <= 1'b0;

      if (!stream_causal || !selected) begin
        bit_count <= 3'b0;
        request_shift <= 8'b0;
      end else if (!previously_selected) begin
        bit_count <= 3'b0;
        request_shift <= 8'b0;
      end else if (sampling_event) begin
        request_shift[current_response_bit] <= pin_in[request_pin];
        if (bit_count == 3'd7) begin
          transfer_valid <= 1'b1;
          transfer_request <= request_live;
          transfer_unknown <=
              (request_live & request_mask) != request_value;
        end else begin
          bit_count <= bit_count + 3'd1;
        end
      end
    end
  end

endmodule

`default_nettype wire
