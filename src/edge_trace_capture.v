/*
 * Copyright (c) 2026 Damir Wallener
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
// Bounded loss-detecting anonymous-pin edge recorder.
module edge_trace_capture #(
    parameter PIN_WIDTH = 4,
    parameter DEPTH = 16,
    parameter DELTA_BITS = 16,
    parameter ADDRESS_BITS = $clog2(DEPTH),
    parameter COUNT_BITS = $clog2(DEPTH + 1)
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    capture_enable,
    input  wire                    clear,
    input  wire [PIN_WIDTH-1:0]    pin_sample,
    input  wire                    pop,
    output wire                    valid,
    output wire [DELTA_BITS-1:0]   event_delta,
    output wire [PIN_WIDTH-1:0]    event_sample,
    output wire [PIN_WIDTH-1:0]    event_changed,
    output reg  [PIN_WIDTH-1:0]    initial_sample,
    output reg  [DELTA_BITS-1:0]   trailing_delta,
    output reg                     capture_complete,
    output reg  [COUNT_BITS-1:0]   event_count,
    output reg                     overflow,
    output wire                    evidence_valid
);

  reg [DELTA_BITS-1:0] delta_memory [0:DEPTH-1];
  reg [PIN_WIDTH-1:0] sample_memory [0:DEPTH-1];
  reg [PIN_WIDTH-1:0] changed_memory [0:DEPTH-1];
  reg [ADDRESS_BITS-1:0] write_pointer;
  reg [ADDRESS_BITS-1:0] read_pointer;
  reg [PIN_WIDTH-1:0] previous_sample;
  reg [DELTA_BITS-1:0] delta_counter;
  reg capturing;
  integer index;

  wire sample_changed = pin_sample != previous_sample;
  wire full = event_count == DEPTH;
  wire write_event = capture_enable && capturing && sample_changed;
  wire accepted_write = write_event && !full;
  wire accepted_pop = pop && valid;

  assign valid = event_count != 0;
  assign event_delta = valid ? delta_memory[read_pointer] : {DELTA_BITS{1'b0}};
  assign event_sample = valid ? sample_memory[read_pointer] : {PIN_WIDTH{1'b0}};
  assign event_changed = valid ? changed_memory[read_pointer] : {PIN_WIDTH{1'b0}};
  assign evidence_valid = !overflow;

  always @(posedge clk) begin
    if (!rst_n || clear) begin
      write_pointer <= {ADDRESS_BITS{1'b0}};
      read_pointer <= {ADDRESS_BITS{1'b0}};
      event_count <= {COUNT_BITS{1'b0}};
      previous_sample <= {PIN_WIDTH{1'b0}};
      delta_counter <= {DELTA_BITS{1'b0}};
      initial_sample <= {PIN_WIDTH{1'b0}};
      trailing_delta <= {DELTA_BITS{1'b0}};
      capture_complete <= 1'b0;
      capturing <= 1'b0;
      overflow <= 1'b0;
      for (index = 0; index < DEPTH; index = index + 1) begin
        delta_memory[index] <= {DELTA_BITS{1'b0}};
        sample_memory[index] <= {PIN_WIDTH{1'b0}};
        changed_memory[index] <= {PIN_WIDTH{1'b0}};
      end
    end else begin
      if (!capture_enable) begin
        if (capturing) begin
          trailing_delta <= delta_counter;
          capture_complete <= 1'b1;
        end
        capturing <= 1'b0;
        delta_counter <= {DELTA_BITS{1'b0}};
      end else if (!capturing) begin
        capturing <= 1'b1;
        previous_sample <= pin_sample;
        initial_sample <= pin_sample;
        trailing_delta <= {DELTA_BITS{1'b0}};
        capture_complete <= 1'b0;
        delta_counter <= {DELTA_BITS{1'b0}};
      end else if (sample_changed) begin
        previous_sample <= pin_sample;
        delta_counter <= {DELTA_BITS{1'b0}};
        if (full) begin
          overflow <= 1'b1;
        end else begin
          delta_memory[write_pointer] <= delta_counter + 1'b1;
          sample_memory[write_pointer] <= pin_sample;
          changed_memory[write_pointer] <= previous_sample ^ pin_sample;
          write_pointer <= write_pointer + 1'b1;
        end
      end else if (&delta_counter) begin
        overflow <= 1'b1;
      end else begin
        delta_counter <= delta_counter + 1'b1;
      end

      if (accepted_pop) begin
        read_pointer <= read_pointer + 1'b1;
      end

      case ({accepted_write, accepted_pop})
        2'b10: event_count <= event_count + 1'b1;
        2'b01: event_count <= event_count - 1'b1;
        default: event_count <= event_count;
      endcase
    end
  end

endmodule

`default_nettype wire
