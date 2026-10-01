/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

// Bounded passive UART-like symbol inference on an unknown one-of-eight pin.
// The bank retains all compatible periods, widths, parity modes, and stop
// counts. It never produces output data or output enable.
module uart_symbol_hypothesis_parallel (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       observe_enable,
    input  wire [7:0] pin_sample,
    output reg        ready,
    output wire       candidate_valid,
    output wire       candidate_ambiguous,
    output reg  [2:0] uart_pin,
    output reg        uart_pin_valid,
    output reg        idle_level,
    output reg  [14:0] bit_period_mask,
    output reg  [4:0] data_width_mask,
    output reg  [2:0] parity_mask,
    output reg  [1:0] stop_count_mask,
    output reg  [9:0] candidate_count,
    output reg  [8:0] decoded_value
);

  reg running;
  reg started;
  reg multiple_active;
  reg [7:0] previous_sample;
  reg [14:0] live_period_mask;
  reg [4:0] phase [2:16];
  reg [4:0] symbol_count [2:16];
  reg [15:0] sampled_symbols [2:16];
  reg [7:0] changed;
  integer seq_pin_index;
  integer seq_period;
  integer comb_period;
  integer comb_width;
  integer comb_parity_kind;
  integer comb_stop_count;
  integer comb_stop_index;
  integer change_count;
  integer changed_pin;
  integer total_symbols;
  integer parity_position;
  integer comb_data_index;
  reg interpretation_valid;
  reg parity_xor;
  reg [8:0] candidate_value;

  assign candidate_valid = ready && uart_pin_valid &&
                           (candidate_count != 0);
  assign candidate_ambiguous = candidate_valid && (candidate_count != 1);

  always @* begin
    candidate_count = 0;
    bit_period_mask = 0;
    data_width_mask = 0;
    parity_mask = 0;
    stop_count_mask = 0;
    decoded_value = 0;
    comb_width = 0;
    comb_parity_kind = 0;
    comb_stop_count = 0;
    comb_stop_index = 0;
    comb_data_index = 0;
    total_symbols = 0;
    parity_position = 0;
    interpretation_valid = 1'b0;
    parity_xor = 1'b0;
    candidate_value = 0;

    for (comb_period = 2; comb_period <= 16;
         comb_period = comb_period + 1) begin
      if (live_period_mask[comb_period - 2]) begin
        for (comb_width = 5; comb_width <= 9;
             comb_width = comb_width + 1) begin
          for (comb_parity_kind = 0; comb_parity_kind < 3;
               comb_parity_kind = comb_parity_kind + 1) begin
            for (comb_stop_count = 1; comb_stop_count <= 2;
                 comb_stop_count = comb_stop_count + 1) begin
              total_symbols = 1 + comb_width +
                              ((comb_parity_kind == 0) ? 0 : 1) +
                              comb_stop_count;
              interpretation_valid =
                  symbol_count[comb_period] >= total_symbols;
              interpretation_valid = interpretation_valid &&
                  (sampled_symbols[comb_period][0] != idle_level);
              candidate_value = 0;
              parity_xor = 0;
              for (comb_data_index = 0; comb_data_index < 9;
                   comb_data_index = comb_data_index + 1) begin
                if (comb_data_index < comb_width) begin
                  candidate_value[comb_data_index] =
                      sampled_symbols[comb_period][1 + comb_data_index];
                  parity_xor = parity_xor ^
                      sampled_symbols[comb_period][1 + comb_data_index];
                end
              end
              parity_position = 1 + comb_width;
              if (comb_parity_kind == 1)
                interpretation_valid = interpretation_valid &&
                    (sampled_symbols[comb_period][parity_position] ==
                     parity_xor);
              else if (comb_parity_kind == 2)
                interpretation_valid = interpretation_valid &&
                    (sampled_symbols[comb_period][parity_position] ==
                     ~parity_xor);

              for (comb_stop_index = 0; comb_stop_index < 2;
                   comb_stop_index = comb_stop_index + 1) begin
                if (comb_stop_index < comb_stop_count)
                  interpretation_valid = interpretation_valid &&
                      (sampled_symbols[comb_period][parity_position +
                       ((comb_parity_kind == 0) ? 0 : 1) +
                       comb_stop_index] == idle_level);
              end

              if (interpretation_valid) begin
                candidate_count = candidate_count + 1'b1;
                bit_period_mask[comb_period - 2] = 1'b1;
                data_width_mask[comb_width - 5] = 1'b1;
                parity_mask[comb_parity_kind] = 1'b1;
                stop_count_mask[comb_stop_count - 1] = 1'b1;
                decoded_value = candidate_value;
              end
            end
          end
        end
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      started <= 1'b0;
      multiple_active <= 1'b0;
      ready <= 1'b0;
      uart_pin <= 0;
      uart_pin_valid <= 1'b0;
      idle_level <= 1'b0;
      previous_sample <= 0;
      live_period_mask <= 0;
      for (seq_period = 2; seq_period <= 16;
           seq_period = seq_period + 1) begin
        phase[seq_period] <= 0;
        symbol_count[seq_period] <= 0;
        sampled_symbols[seq_period] <= 0;
      end
    end else if (observe_enable && !running) begin
      running <= 1'b1;
      started <= 1'b0;
      multiple_active <= 1'b0;
      ready <= 1'b0;
      uart_pin_valid <= 1'b0;
      previous_sample <= pin_sample;
      live_period_mask <= 15'h7fff;
      for (seq_period = 2; seq_period <= 16;
           seq_period = seq_period + 1) begin
        phase[seq_period] <= 0;
        symbol_count[seq_period] <= 0;
        sampled_symbols[seq_period] <= 0;
      end
    end else if (observe_enable && running) begin
      changed = previous_sample ^ pin_sample;
      previous_sample <= pin_sample;
      change_count = 0;
      changed_pin = 0;
      for (seq_pin_index = 0; seq_pin_index < 8;
           seq_pin_index = seq_pin_index + 1) begin
        if (changed[seq_pin_index]) begin
          change_count = change_count + 1;
          changed_pin = seq_pin_index;
        end
      end

      if (!started && (change_count != 0)) begin
        if (change_count == 1) begin
          started <= 1'b1;
          uart_pin <= changed_pin;
          idle_level <= previous_sample[changed_pin];
        end else begin
          multiple_active <= 1'b1;
        end
      end else if (started) begin
        for (seq_pin_index = 0; seq_pin_index < 8;
             seq_pin_index = seq_pin_index + 1)
          if ((seq_pin_index != uart_pin) && changed[seq_pin_index])
            multiple_active <= 1'b1;

        for (seq_period = 2; seq_period <= 16;
             seq_period = seq_period + 1) begin
          if (live_period_mask[seq_period - 2]) begin
            if (changed[uart_pin] &&
                (phase[seq_period] != seq_period - 1))
              live_period_mask[seq_period - 2] <= 1'b0;
            if ((phase[seq_period] == ((seq_period / 2) - 1)) &&
                (symbol_count[seq_period] < 16)) begin
              sampled_symbols[seq_period][symbol_count[seq_period]] <=
                  pin_sample[uart_pin];
              symbol_count[seq_period] <=
                  symbol_count[seq_period] + 1'b1;
            end
            if (phase[seq_period] == seq_period - 1)
              phase[seq_period] <= 0;
            else
              phase[seq_period] <= phase[seq_period] + 1'b1;
          end
        end
      end
    end else if (!observe_enable && running) begin
      running <= 1'b0;
      ready <= 1'b1;
      uart_pin_valid <= started && !multiple_active;
    end
  end

endmodule

`default_nettype wire
