`timescale 1ns/1ps
`default_nettype none

module integrated_interrogation_top_tb;
  reg clk = 0;
  reg rst_n = 0;
  reg ena = 1;
  reg [7:0] ui_in = 0;
  reg host_scl_low = 0;
  reg host_sda_low = 0;
  wire [7:0] uo_out;
  wire [7:0] uio_in;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  localparam [7:0] DISCOVER = 8'h01;
  localparam [7:0] OWNERSHIP = 8'h08;
  localparam [7:0] ACTIVATE = 8'h10;
  localparam [7:0] REVOKE = 8'h20;
  localparam [2:0] CLOCK_PIN = 3'd2;
  localparam [2:0] DATA_PIN = 3'd5;
  localparam integer SECRET_BIT = 5;

  integer probe_count = 0;
  integer wait_count = 0;
  reg [7:0] status_value;
  reg [4:0] previous_candidate_count;

  tri scl;
  tri sda;
  pullup (weak1) scl_pullup(scl);
  pullup (weak1) sda_pullup(sda);
  assign (strong0, highz1) scl = host_scl_low ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = host_sda_low ? 1'b0 : 1'bz;
  assign (strong0, highz1) scl = uio_oe[CLOCK_PIN] ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = uio_oe[DATA_PIN] ? 1'b0 : 1'bz;
  assign uio_in = {2'b11, sda, 2'b11, scl, 2'b11};

  open_drain_bit_target_model #(.SECRET_BIT(SECRET_BIT)) target (
      .scl(scl), .sda(sda)
  );

  tt_um_dwallener_mindreader dut (
      .ui_in(ui_in), .uo_out(uo_out), .uio_in(uio_in),
      .uio_out(uio_out), .uio_oe(uio_oe), .ena(ena),
      .clk(clk), .rst_n(rst_n)
  );

  always #5 clk = ~clk;
  always @* begin
    if ((uio_oe & uio_out) != 0)
      fail("interrogation attempted active-high drive");
    if ((uio_oe & ~((8'b1 << CLOCK_PIN) | (8'b1 << DATA_PIN))) != 0)
      fail("interrogation drove an uninferred pin");
  end

  function [7:0] page_input;
    input [4:0] page;
    begin
      page_input = 8'h80 |
                   ({7'b0, page[4]} << 1) |
                   ({6'b0, page[3:2]} << 2) |
                   ({6'b0, page[1:0]} << 5);
    end
  endfunction

  task tick;
    input integer cycles;
    integer cycle;
    begin
      for (cycle = 0; cycle < cycles; cycle = cycle + 1) begin
        @(posedge clk);
        #1;
      end
    end
  endtask

  task lines;
    input scl_low;
    input sda_low;
    begin
      host_scl_low = scl_low;
      host_sda_low = sda_low;
      tick(1);
    end
  endtask

  task passive_frame;
    input [6:0] request;
    integer bit_no;
    reg [7:0] value;
    begin
      value = {request, 1'b0};
      ui_in = DISCOVER;
      lines(0, 0);
      lines(0, 1);
      for (bit_no = 7; bit_no >= 0; bit_no = bit_no - 1) begin
        lines(1, !value[bit_no]);
        lines(0, !value[bit_no]);
        lines(1, !value[bit_no]);
      end
      lines(1, 0);
      lines(0, 0);
      lines(1, 0);
      lines(1, 1);
      lines(0, 1);
      lines(0, 0);
      ui_in = 0;
      tick(4);
      if (uio_oe != 0)
        fail("passive capture drove the bus");
    end
  endtask

  task read_page;
    input [4:0] page;
    output [7:0] value;
    begin
      ui_in = page_input(page);
      #1;
      value = uo_out;
    end
  endtask

  task reset_and_train;
    begin
      ui_in = 0;
      ena = 1;
      host_scl_low = 0;
      host_sda_low = 0;
      rst_n = 0;
      tick(2);
      rst_n = 1;
      tick(2);
      passive_frame(7'h00);
      passive_frame(7'h7f);
      read_page(5'h1d, status_value);
      if (status_value[4:0] != 5'd7)
        fail("passive traffic did not produce seven candidates");
    end
  endtask

  task wait_for_proposal;
    begin
      wait_count = 0;
      read_page(5'h1c, status_value);
      while (!status_value[6]) begin
        tick(1);
        read_page(5'h1c, status_value);
        wait_count = wait_count + 1;
        if (wait_count > 132)
          fail("integrated proposal search timeout");
      end
      if (!status_value[0])
        fail("proposal exists without accepted passive evidence");
    end
  endtask

  task launch_one_probe;
    begin
      ui_in = OWNERSHIP | ACTIVATE;
      tick(1);
      ui_in = OWNERSHIP;
      tick(48);
      probe_count = probe_count + 1;
    end
  endtask

  task fail;
    input [8*160-1:0] message;
    begin
      $display("FAIL: %0s", message);
      $finish(1);
    end
  endtask

  initial begin
    reset_and_train();
    wait_for_proposal();

    // No ownership means no electrical activity even with activation high.
    ui_in = ACTIVATE;
    tick(4);
    if (uio_oe != 0)
      fail("unauthorized activation drove the bus");
    ui_in = 0;
    tick(1);

    // Holding activation high may launch one probe only. Even after the next
    // proposal becomes ready it must wait for a new low-to-high request.
    wait_for_proposal();
    read_page(5'h1d, status_value);
    previous_candidate_count = status_value[4:0];
    ui_in = OWNERSHIP | ACTIVATE;
    tick(200);
    ui_in = OWNERSHIP;
    tick(1);
    probe_count = probe_count + 1;
    read_page(5'h1d, status_value);
    if (status_value[4:0] != 5'd4 ||
        status_value[4:0] >= previous_candidate_count)
      fail("activation level launched zero or multiple probes");
    read_page(5'h1c, status_value);

    while (!status_value[7]) begin
      wait_for_proposal();
      read_page(5'h1d, status_value);
      previous_candidate_count = status_value[4:0];
      launch_one_probe();
      read_page(5'h1d, status_value);
      if (status_value[4:0] >= previous_candidate_count)
        fail("probe did not reduce candidates");
      read_page(5'h1c, status_value);
      if (probe_count > 3)
        fail("integrated probe budget exceeded");
    end

    read_page(5'h1f, status_value);
    if (!status_value[7] || status_value[6] || status_value[5:3] != SECRET_BIT)
      fail("integrated interrogation resolved wrong behavior");
    if (uio_oe != 0)
      fail("resolved interrogation did not release bus");

    // Re-train, launch a probe, and prove combinational revoke release.
    reset_and_train();
    wait_for_proposal();
    ui_in = OWNERSHIP | ACTIVATE;
    tick(1);
    ui_in = OWNERSHIP;
    wait_count = 0;
    while (uio_oe == 0) begin
      tick(1);
      wait_count = wait_count + 1;
      if (wait_count > 12)
        fail("probe never acquired open-drain output enable");
    end
    ui_in = OWNERSHIP | REVOKE;
    #1;
    if (uio_oe != 0)
      fail("revoke did not release pads combinationally");
    tick(2);

    // Clear requires recapture and must leave the interrogation path passive.
    ui_in = 8'h40;
    tick(1);
    ui_in = 0;
    tick(1);
    read_page(5'h1d, status_value);
    if (status_value[4:0] != 5'd14 || uio_oe != 0)
      fail("fault clear did not reset interrogation evidence");

    // Repeat far enough to acquire a pad, then prove TinyTapeout disable.
    reset_and_train();
    wait_for_proposal();
    ui_in = OWNERSHIP | ACTIVATE;
    tick(1);
    ui_in = OWNERSHIP;
    while (uio_oe == 0)
      tick(1);
    ena = 0;
    #1;
    if (uio_oe != 0 || uio_out != 0 || uo_out != 0)
      fail("ena=0 did not release and quiet TinyTapeout outputs");

    $display("INTEGRATED INTERROGATION TOP PASS: probes=%0d winner_bit=%0d",
             probe_count, SECRET_BIT);
    $finish(0);
  end
endmodule

`default_nettype wire
