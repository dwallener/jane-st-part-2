`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,enable=0,timing_enable=0,clear_fault=0,monitor_enable=0,drive_requested=0;
reg [3:0] pins=4'b1000,driven=0,oe=0; reg [7:0] req,resp; integer i;
wire valid,aborted,timing_observed,timing_safe,timing_violation,mismatch_now,drive_allow,contention_fault;
wire [7:0] a,b;
always #5 clk=~clk;
spi_transaction_decoder d(.clk(clk),.rst_n(rst_n),.enable(enable),.pin_sample(pins),.select_pin(2'd3),.clock_pin(2'd0),.data_a_pin(2'd1),.data_b_pin(2'd2),.select_active_level(0),.clock_idle_level(0),.sample_trailing(1),.transaction_valid(valid),.transaction_aborted(aborted),.data_a_word(a),.data_b_word(b));
spi_timing_guard t(.clk(clk),.rst_n(rst_n),.observe_enable(timing_enable),.pin_sample(pins),.select_pin(2'd3),.clock_pin(2'd0),.select_active_level(0),.clock_idle_level(0),.sample_trailing(1),.minimum_half_ticks(1),.minimum_select_ticks(1),.timing_observed(timing_observed),.timing_safe(timing_safe),.timing_violation(timing_violation));
pin_contention_monitor m(.clk(clk),.rst_n(rst_n),.clear_fault(clear_fault),.monitor_enable(monitor_enable),.drive_requested(drive_requested),.pin_in(pins),.pin_out(driven),.pin_oe(oe),.mismatch_now(mismatch_now),.drive_allow(drive_allow),.contention_fault(contention_fault));
task tick;begin @(posedge clk);#1;end endtask
task fail;input[799:0]s;begin $display("FAIL %0s",s);$finish(1);end endtask
task begin_frame;begin pins=4'b1000;tick();pins[3]=0;tick();end endtask
task send_bit;input x,y;begin pins[1]=x;pins[2]=y;pins[0]=1;tick();tick();pins[0]=0;tick();tick();end endtask
task end_frame;begin pins[3]=1;tick();end endtask
initial begin req=8'hA7;resp=8'h63;repeat(2)tick();rst_n=1;enable=1;timing_enable=1;
 begin_frame();for(i=7;i>=0;i=i-1)send_bit(req[i],resp[i]);end_frame();if(!valid||aborted||a!=req||b!=resp)fail("exact");tick();if(!timing_observed||!timing_safe||timing_violation)fail("timing");
 begin_frame();for(i=7;i>=0;i=i-1)send_bit(req[i],resp[i]);end_frame();if(!valid||aborted||a!=req||b!=resp)fail("back-to-back first");pins[3]=0;tick();for(i=7;i>=0;i=i-1)send_bit(~req[i],~resp[i]);end_frame();if(!valid||aborted||a!=~req||b!=~resp)fail("back-to-back second");tick();
 begin_frame();for(i=7;i>=5;i=i-1)send_bit(req[i],resp[i]);end_frame();if(valid||!aborted)fail("short");tick();
 begin_frame();for(i=7;i>=0;i=i-1)send_bit(req[i],resp[i]);send_bit(0,0);end_frame();if(valid||!aborted)fail("long");tick();
 begin_frame();end_frame();if(valid||aborted)fail("glitch");tick();begin_frame();send_bit(1,0);rst_n=0;tick();if(valid||aborted)fail("reset");rst_n=1;tick();
 monitor_enable=1;drive_requested=1;oe=4'b0100;driven=4'b0100;pins=4'b0100;#1;if(!drive_allow||mismatch_now)fail("loopback");pins=0;#1;if(drive_allow||!mismatch_now)fail("immediate");tick();if(!contention_fault)fail("latch");clear_fault=1;tick();if(contention_fault)fail("clear");
 $display("SPI BOUNDARY PASS");$finish(0);end
endmodule
