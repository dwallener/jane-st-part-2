/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// One bounded open-drain address probe. The engine emits an I2C-compatible
// START, seven-bit address plus write bit, ACK sample, and STOP. Every driven
// bit is zero; a one is represented only by releasing the selected pin.
module open_drain_address_probe #(
    parameter [7:0] WAIT_LIMIT = 8'd32
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire       authorize,
    input  wire       abort_request,
    input  wire [2:0] clock_pin,
    input  wire [2:0] data_pin,
    input  wire [6:0] address,
    input  wire [7:0] pin_in,
    output wire [7:0] pin_out,
    output wire [7:0] pin_oe,
    output wire       busy,
    output reg        done,
    output reg        acknowledged,
    output reg        timed_out,
    output reg        revoked
);

  localparam STATE_IDLE       = 4'd0;
  localparam STATE_BUS_FREE   = 4'd1;
  localparam STATE_START      = 4'd2;
  localparam STATE_BIT_LOW    = 4'd3;
  localparam STATE_BIT_RISE   = 4'd4;
  localparam STATE_BIT_HIGH   = 4'd5;
  localparam STATE_ACK_LOW    = 4'd6;
  localparam STATE_ACK_RISE   = 4'd7;
  localparam STATE_ACK_HIGH   = 4'd8;
  localparam STATE_STOP_LOW   = 4'd9;
  localparam STATE_STOP_RISE  = 4'd10;
  localparam STATE_STOP_HIGH  = 4'd11;
  localparam STATE_FINISH     = 4'd12;
  localparam STATE_FAULT      = 4'd13;

  reg [3:0] state;
  reg [2:0] bit_index;
  reg [7:0] wait_count;
  reg [7:0] address_write;
  reg clock_low;
  reg data_low;

  wire clock_level = pin_in[clock_pin];
  wire data_level = pin_in[data_pin];
  wire authority_live = authorize && !abort_request;

  assign busy = (state != STATE_IDLE) && (state != STATE_FINISH) &&
                (state != STATE_FAULT);
  assign pin_out = 8'h00;
  // Authorization gates output enable combinationally. State may take a clock
  // to report revocation, but the pins release immediately.
  assign pin_oe = authority_live
      ? ((clock_low ? (8'b1 << clock_pin) : 8'h00) |
         (data_low ? (8'b1 << data_pin) : 8'h00))
      : 8'h00;

  always @* begin
    clock_low = 1'b0;
    data_low = 1'b0;
    case (state)
      STATE_START: begin
        data_low = 1'b1;
      end
      STATE_BIT_LOW: begin
        clock_low = 1'b1;
        data_low = ~address_write[bit_index];
      end
      STATE_BIT_RISE, STATE_BIT_HIGH: begin
        data_low = ~address_write[bit_index];
      end
      STATE_ACK_LOW: begin
        clock_low = 1'b1;
      end
      STATE_STOP_LOW: begin
        clock_low = 1'b1;
        data_low = 1'b1;
      end
      STATE_STOP_RISE: begin
        data_low = 1'b1;
      end
      default: begin
        clock_low = 1'b0;
        data_low = 1'b0;
      end
    endcase
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      state <= STATE_IDLE;
      bit_index <= 0;
      wait_count <= 0;
      address_write <= 0;
      done <= 1'b0;
      acknowledged <= 1'b0;
      timed_out <= 1'b0;
      revoked <= 1'b0;
    end else begin
      done <= 1'b0;

      if ((state != STATE_IDLE) && (state != STATE_FINISH) &&
          (state != STATE_FAULT) && !authority_live) begin
        state <= STATE_FAULT;
        revoked <= 1'b1;
      end else begin
        case (state)
          STATE_IDLE: begin
            wait_count <= 0;
            if (start && authorize && !abort_request) begin
              state <= STATE_BUS_FREE;
              address_write <= {address, 1'b0};
              bit_index <= 3'd7;
              acknowledged <= 1'b0;
              timed_out <= 1'b0;
              revoked <= 1'b0;
            end
          end
          STATE_BUS_FREE: begin
            if (clock_level && data_level) begin
              state <= STATE_START;
              wait_count <= 0;
            end else if (wait_count == WAIT_LIMIT) begin
              state <= STATE_FAULT;
              timed_out <= 1'b1;
            end else begin
              wait_count <= wait_count + 1'b1;
            end
          end
          STATE_START: begin
            state <= STATE_BIT_LOW;
          end
          STATE_BIT_LOW: begin
            state <= STATE_BIT_RISE;
            wait_count <= 0;
          end
          STATE_BIT_RISE: begin
            if (clock_level) begin
              state <= STATE_BIT_HIGH;
              wait_count <= 0;
            end else if (wait_count == WAIT_LIMIT) begin
              state <= STATE_FAULT;
              timed_out <= 1'b1;
            end else begin
              wait_count <= wait_count + 1'b1;
            end
          end
          STATE_BIT_HIGH: begin
            if (bit_index == 0)
              state <= STATE_ACK_LOW;
            else begin
              bit_index <= bit_index - 1'b1;
              state <= STATE_BIT_LOW;
            end
          end
          STATE_ACK_LOW: begin
            state <= STATE_ACK_RISE;
            wait_count <= 0;
          end
          STATE_ACK_RISE: begin
            if (clock_level) begin
              state <= STATE_ACK_HIGH;
              wait_count <= 0;
            end else if (wait_count == WAIT_LIMIT) begin
              state <= STATE_FAULT;
              timed_out <= 1'b1;
            end else begin
              wait_count <= wait_count + 1'b1;
            end
          end
          STATE_ACK_HIGH: begin
            acknowledged <= ~data_level;
            state <= STATE_STOP_LOW;
          end
          STATE_STOP_LOW: begin
            state <= STATE_STOP_RISE;
            wait_count <= 0;
          end
          STATE_STOP_RISE: begin
            if (clock_level) begin
              state <= STATE_STOP_HIGH;
              wait_count <= 0;
            end else if (wait_count == WAIT_LIMIT) begin
              state <= STATE_FAULT;
              timed_out <= 1'b1;
            end else begin
              wait_count <= wait_count + 1'b1;
            end
          end
          STATE_STOP_HIGH: begin
            state <= STATE_FINISH;
          end
          STATE_FINISH: begin
            done <= 1'b1;
            state <= STATE_IDLE;
          end
          STATE_FAULT: begin
            done <= 1'b1;
            state <= STATE_IDLE;
          end
          default: begin
            state <= STATE_FAULT;
            revoked <= 1'b1;
          end
        endcase
      end
    end
  end

endmodule

`default_nettype wire
