/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module spi_transaction_decoder (
    input wire clk, input wire rst_n, input wire enable,
    input wire [7:0] pin_sample,
    input wire [2:0] select_pin, input wire [2:0] clock_pin,
    input wire [2:0] data_a_pin, input wire [2:0] data_b_pin,
    input wire select_active_level, input wire clock_idle_level,
    input wire sample_trailing,
    output reg transaction_valid, output reg transaction_aborted,
    output reg [7:0] data_a_word, output reg [7:0] data_b_word
);
  reg [7:0] previous_sample;
  reg previous_selected;
  reg [3:0] bit_count;
  reg overlong;
  reg [6:0] shift_a;
  reg [6:0] shift_b;
  wire selected = pin_sample[select_pin] == select_active_level;
  wire leading = previous_sample[clock_pin] == clock_idle_level &&
                 pin_sample[clock_pin] != clock_idle_level;
  wire trailing = previous_sample[clock_pin] != clock_idle_level &&
                  pin_sample[clock_pin] == clock_idle_level;
  wire sample_now = selected && (sample_trailing ? trailing : leading);

  always @(posedge clk) begin
    if (!rst_n) begin
      previous_sample <= 0;
      previous_selected <= 0;
      bit_count <= 0;
      overlong <= 0;
      shift_a <= 0;
      shift_b <= 0;
      transaction_valid <= 0;
      transaction_aborted <= 0;
      data_a_word <= 0;
      data_b_word <= 0;
    end else begin
      previous_sample <= pin_sample;
      previous_selected <= selected;
      transaction_valid <= 0;
      transaction_aborted <= 0;
      if (!enable) begin
        bit_count <= 0;
        overlong <= 0;
        shift_a <= 0;
        shift_b <= 0;
      end else if (selected && !previous_selected) begin
        bit_count <= 0;
        overlong <= 0;
        shift_a <= 0;
        shift_b <= 0;
      end else if (!selected && previous_selected) begin
        if ((bit_count == 8) && !overlong) transaction_valid <= 1;
        else if (bit_count != 0 || overlong) transaction_aborted <= 1;
        bit_count <= 0;
        overlong <= 0;
      end else if (sample_now) begin
        if (bit_count < 8) begin
          shift_a <= {shift_a[5:0], pin_sample[data_a_pin]};
          shift_b <= {shift_b[5:0], pin_sample[data_b_pin]};
          bit_count <= bit_count + 1'b1;
        end else overlong <= 1;
        if (bit_count == 7) begin
          data_a_word <= {shift_a[6:0], pin_sample[data_a_pin]};
          data_b_word <= {shift_b[6:0], pin_sample[data_b_pin]};
        end
      end
    end
  end
endmodule
`default_nettype wire
