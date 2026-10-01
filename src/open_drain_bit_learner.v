/* Copyright (c) 2026 Damir Wallener; SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
// Learn whether ACK is copy/invert of one of seven request bits. A single
// scoring datapath searches the 128 possible requests over 128 clocks, rather
// than materializing 128 copies of that datapath in combinational logic.
module open_drain_bit_learner (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        observe_valid,
    input  wire [6:0]  observed_request,
    input  wire        observed_ack,
    output reg  [13:0] candidate_mask,
    output reg  [4:0]  candidate_count,
    output reg          proposal_valid,
    output reg  [6:0]  proposal_request,
    output wire         resolved,
    output reg          winner_invert,
    output reg  [2:0]  winner_bit
);

  integer count_index;
  integer update_index;
  reg [6:0] search_request;
  reg [3:0] prediction_zero_count;
  reg [3:0] prediction_one_count;
  reg [3:0] current_partition;
  reg [3:0] best_partition;
  reg       current_is_split;
  reg       found_split;

  assign resolved = candidate_count == 1;

  // Candidate summary and the score for the one request under consideration.
  always @* begin
    candidate_count = 0;
    winner_invert = 1'b0;
    winner_bit = 0;
    prediction_zero_count = 0;
    prediction_one_count = 0;
    for (count_index = 0; count_index < 14; count_index = count_index + 1) begin
      if (candidate_mask[count_index]) begin
        candidate_count = candidate_count + 1'b1;
        winner_invert = count_index >= 7;
        if (count_index >= 7)
          winner_bit = count_index[2:0] - 3'd7;
        else
          winner_bit = count_index[2:0];

        if (count_index < 7) begin
          if (search_request[count_index])
            prediction_one_count = prediction_one_count + 1'b1;
          else
            prediction_zero_count = prediction_zero_count + 1'b1;
        end else begin
          if (!search_request[count_index - 7])
            prediction_one_count = prediction_one_count + 1'b1;
          else
            prediction_zero_count = prediction_zero_count + 1'b1;
        end
      end
    end
    current_is_split = (prediction_zero_count != 0) &&
                       (prediction_one_count != 0);
    current_partition = (prediction_zero_count > prediction_one_count)
        ? prediction_zero_count : prediction_one_count;
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      candidate_mask <= 14'h3fff;
      proposal_valid <= 1'b0;
      proposal_request <= 0;
      search_request <= 0;
      best_partition <= 4'hf;
      found_split <= 1'b0;
    end else if (observe_valid) begin
      for (update_index = 0; update_index < 7;
           update_index = update_index + 1) begin
        candidate_mask[update_index] <=
            candidate_mask[update_index] &&
            (observed_request[update_index] == observed_ack);
        candidate_mask[update_index + 7] <=
            candidate_mask[update_index + 7] &&
            ((~observed_request[update_index]) == observed_ack);
      end
      // New evidence invalidates the old proposal and starts a fresh scan.
      proposal_valid <= 1'b0;
      search_request <= 0;
      best_partition <= 4'hf;
      found_split <= 1'b0;
    end else if (!proposal_valid && candidate_count > 1) begin
      if (current_is_split &&
          (!found_split || current_partition < best_partition)) begin
        found_split <= 1'b1;
        best_partition <= current_partition;
        proposal_request <= search_request;
      end

      if (search_request == 7'h7f) begin
        proposal_valid <= found_split || current_is_split;
        if (current_is_split &&
            (!found_split || current_partition < best_partition))
          proposal_request <= search_request;
      end else begin
        search_request <= search_request + 1'b1;
      end
    end
  end
endmodule
`default_nettype wire
