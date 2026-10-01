/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Bounded passive UART-like symbol inference on an unknown one-of-eight pin.
// Capture maintains period hypotheses concurrently. After capture, one shared
// evaluator scans the 450 period/width/parity/stop combinations in 450 clocks.
// The block never produces output data or output enable.
module uart_symbol_hypothesis (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        observe_enable,
    input  wire [7:0]  pin_sample,
    output reg         ready,
    output wire        candidate_valid,
    output wire        candidate_ambiguous,
    output reg  [2:0]  uart_pin,
    output reg         uart_pin_valid,
    output reg         idle_level,
    output reg  [14:0] bit_period_mask,
    output reg  [4:0]  data_width_mask,
    output reg  [2:0]  parity_mask,
    output reg  [1:0]  stop_count_mask,
    output reg  [9:0]  candidate_count,
    output reg  [8:0]  decoded_value
);

  reg running;
  reg started;
  reg multiple_active;
  reg evaluating;
  reg [7:0] previous_sample;
  reg [14:0] live_period_mask;
  // Indices zero and one are deliberately present and held at zero. This
  // makes the dynamic evaluator mux total even though legal periods are 2–16.
  reg [4:0] phase [0:16];
  reg [4:0] symbol_count [0:16];
  reg [15:0] sampled_symbols [0:16];

  reg [4:0] eval_period;
  reg [3:0] eval_width;
  reg [1:0] eval_parity;
  reg [1:0] eval_stops;

  reg [7:0] changed;
  integer seq_pin_index;
  integer seq_period;
  integer change_count;
  integer changed_pin;

  integer eval_data_index;
  integer eval_stop_index;
  reg [4:0] eval_total_symbols;
  reg [3:0] eval_parity_position;
  reg current_valid;
  reg current_parity_xor;
  reg [8:0] current_value;

  assign candidate_valid = ready && uart_pin_valid &&
                           (candidate_count != 0);
  assign candidate_ambiguous = candidate_valid && (candidate_count != 1);

  // Only one candidate is evaluated at a time. Dynamic reads are bounded by
  // the evaluator counters and replace 450 parallel copies of this logic.
  always @* begin
    eval_data_index = 0;
    eval_stop_index = 0;
    eval_total_symbols = 0;
    eval_parity_position = 0;
    current_valid = 1'b0;
    current_parity_xor = 1'b0;
    current_value = 0;

    if (evaluating) begin
      eval_total_symbols = 5'd1 + {1'b0, eval_width} +
                           ((eval_parity == 0) ? 5'd0 : 5'd1) +
                           {3'b000, eval_stops};
      current_valid = live_period_mask[eval_period - 2] &&
                      (symbol_count[eval_period] >= eval_total_symbols) &&
                      (sampled_symbols[eval_period][0] != idle_level);

      for (eval_data_index = 0; eval_data_index < 9;
           eval_data_index = eval_data_index + 1) begin
        if (eval_data_index < eval_width) begin
          current_value[eval_data_index] =
              sampled_symbols[eval_period][1 + eval_data_index];
          current_parity_xor = current_parity_xor ^
              sampled_symbols[eval_period][1 + eval_data_index];
        end
      end

      eval_parity_position = 4'd1 + eval_width;
      if (eval_parity == 1)
        current_valid = current_valid &&
            (sampled_symbols[eval_period][eval_parity_position] ==
             current_parity_xor);
      else if (eval_parity == 2)
        current_valid = current_valid &&
            (sampled_symbols[eval_period][eval_parity_position] ==
             ~current_parity_xor);

      for (eval_stop_index = 0; eval_stop_index < 2;
           eval_stop_index = eval_stop_index + 1) begin
        if (eval_stop_index < eval_stops)
          current_valid = current_valid &&
              (sampled_symbols[eval_period][eval_parity_position +
               ((eval_parity == 0) ? 4'd0 : 4'd1) +
               {3'b000, eval_stop_index[0]}] == idle_level);
      end
    end
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      running <= 1'b0;
      started <= 1'b0;
      multiple_active <= 1'b0;
      evaluating <= 1'b0;
      ready <= 1'b0;
      uart_pin <= 0;
      uart_pin_valid <= 1'b0;
      idle_level <= 1'b0;
      previous_sample <= 0;
      live_period_mask <= 0;
      eval_period <= 2;
      eval_width <= 5;
      eval_parity <= 0;
      eval_stops <= 1;
      bit_period_mask <= 0;
      data_width_mask <= 0;
      parity_mask <= 0;
      stop_count_mask <= 0;
      candidate_count <= 0;
      decoded_value <= 0;
      for (seq_period = 0; seq_period <= 16;
           seq_period = seq_period + 1) begin
        phase[seq_period] <= 0;
        symbol_count[seq_period] <= 0;
        sampled_symbols[seq_period] <= 0;
      end
    end else if (observe_enable && !running && !evaluating) begin
      running <= 1'b1;
      started <= 1'b0;
      multiple_active <= 1'b0;
      ready <= 1'b0;
      uart_pin_valid <= 1'b0;
      previous_sample <= pin_sample;
      live_period_mask <= 15'h7fff;
      bit_period_mask <= 0;
      data_width_mask <= 0;
      parity_mask <= 0;
      stop_count_mask <= 0;
      candidate_count <= 0;
      decoded_value <= 0;
      for (seq_period = 0; seq_period <= 16;
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
          uart_pin <= changed_pin[2:0];
          idle_level <= previous_sample[changed_pin];
        end else begin
          multiple_active <= 1'b1;
        end
      end else if (started) begin
        for (seq_pin_index = 0; seq_pin_index < 8;
             seq_pin_index = seq_pin_index + 1)
          if ((seq_pin_index[2:0] != uart_pin) && changed[seq_pin_index])
            multiple_active <= 1'b1;

        for (seq_period = 2; seq_period <= 16;
             seq_period = seq_period + 1) begin
          if (live_period_mask[seq_period - 2]) begin
            if (changed[uart_pin] &&
                (phase[seq_period] != (seq_period[4:0] - 5'd1)))
              live_period_mask[seq_period - 2] <= 1'b0;
            if ((phase[seq_period] ==
                 ((seq_period[4:0] >> 1) - 5'd1)) &&
                (symbol_count[seq_period] < 16)) begin
              sampled_symbols[seq_period][symbol_count[seq_period][3:0]] <=
                  pin_sample[uart_pin];
              symbol_count[seq_period] <=
                  symbol_count[seq_period] + 1'b1;
            end
            if (phase[seq_period] == (seq_period[4:0] - 5'd1))
              phase[seq_period] <= 0;
            else
              phase[seq_period] <= phase[seq_period] + 1'b1;
          end
        end
      end
    end else if (!observe_enable && running) begin
      running <= 1'b0;
      uart_pin_valid <= started && !multiple_active;
      if (started && !multiple_active) begin
        evaluating <= 1'b1;
        eval_period <= 2;
        eval_width <= 5;
        eval_parity <= 0;
        eval_stops <= 1;
      end else begin
        ready <= 1'b1;
      end
    end else if (evaluating) begin
      if (current_valid) begin
        candidate_count <= candidate_count + 1'b1;
        bit_period_mask[eval_period - 2] <= 1'b1;
        data_width_mask[eval_width - 5] <= 1'b1;
        parity_mask[eval_parity] <= 1'b1;
        stop_count_mask[eval_stops - 1] <= 1'b1;
        decoded_value <= current_value;
      end

      if (eval_stops == 2) begin
        eval_stops <= 1;
        if (eval_parity == 2) begin
          eval_parity <= 0;
          if (eval_width == 9) begin
            eval_width <= 5;
            if (eval_period == 16) begin
              evaluating <= 1'b0;
              ready <= 1'b1;
            end else begin
              eval_period <= eval_period + 1'b1;
            end
          end else begin
            eval_width <= eval_width + 1'b1;
          end
        end else begin
          eval_parity <= eval_parity + 1'b1;
        end
      end else begin
        eval_stops <= eval_stops + 1'b1;
      end
    end
  end

endmodule

`default_nettype wire
