/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
`timescale 1ns / 1ps

module template_spi_peripheral (
    input wire clk, input wire rst_n, input wire drive_enable,
    input wire [7:0] pin_in,
    input wire [2:0] select_pin, input wire [2:0] clock_pin,
    input wire [2:0] request_pin, input wire [2:0] response_pin,
    input wire select_active_level, input wire clock_idle_level,
    input wire sample_trailing,
    input wire [7:0] request_mask, input wire [7:0] request_value,
    input wire [143:0] candidate_masks,
    output reg [7:0] pin_out, output reg [7:0] pin_oe,
    output reg transfer_valid, output reg [7:0] transfer_request,
    output reg transfer_unknown
);
  reg [7:0] previous_pins;
  reg previous_selected;
  reg [2:0] bit_count;
  reg [7:0] request_shift, request_live;
  reg response_value;
  integer current_bit, expression_index, selected_code;
  wire selected = pin_in[select_pin] == select_active_level;
  wire leading = previous_pins[clock_pin] == clock_idle_level &&
                 pin_in[clock_pin] != clock_idle_level;
  wire trailing = previous_pins[clock_pin] != clock_idle_level &&
                  pin_in[clock_pin] == clock_idle_level;
  wire sample_now = selected && (sample_trailing ? trailing : leading);

  always @* begin
    current_bit = 7 - bit_count;
    request_live = request_shift;
    request_live[current_bit] = pin_in[request_pin];
    selected_code = 0;
    for (expression_index = 0; expression_index < 18;
         expression_index = expression_index + 1)
      if (candidate_masks[current_bit * 18 + expression_index])
        selected_code = expression_index;
    if (selected_code == 0) response_value = 0;
    else if (selected_code == 1) response_value = 1;
    else begin
      response_value = request_live[(selected_code - 2) >> 1];
      if (selected_code[0]) response_value = ~response_value;
    end
    pin_out = 0;
    pin_oe = 0;
    if (drive_enable && selected) begin
      pin_out[response_pin] = response_value;
      pin_oe[response_pin] = 1;
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      previous_pins <= 0;
      previous_selected <= 0;
      bit_count <= 0;
      request_shift <= 0;
      transfer_valid <= 0;
      transfer_request <= 0;
      transfer_unknown <= 0;
    end else begin
      previous_pins <= pin_in;
      previous_selected <= selected;
      transfer_valid <= 0;
      if (!drive_enable || !selected) begin
        bit_count <= 0;
        request_shift <= 0;
      end else if (!previous_selected) begin
        bit_count <= 0;
        request_shift <= 0;
      end else if (sample_now) begin
        request_shift[current_bit] <= pin_in[request_pin];
        if (bit_count == 7) begin
          transfer_valid <= 1;
          transfer_request <= request_live;
          transfer_unknown <= (request_live & request_mask) != request_value;
        end else bit_count <= bit_count + 1'b1;
      end
    end
  end
endmodule
`default_nettype wire
