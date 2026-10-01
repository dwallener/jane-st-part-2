`default_nettype none
module pin_contention_monitor #(parameter WIDTH=4)(input wire clk,rst_n,clear_fault,monitor_enable,drive_requested,
 input wire [WIDTH-1:0] pin_in,pin_out,pin_oe,output wire mismatch_now,drive_allow,output reg contention_fault);
assign mismatch_now=monitor_enable&&drive_requested&&|(pin_oe&(pin_in^pin_out));
assign drive_allow=drive_requested&&!mismatch_now&&!contention_fault;
always @(posedge clk)if(!rst_n||clear_fault)contention_fault<=0;else if(mismatch_now)contention_fault<=1;
endmodule
`default_nettype wire
