`default_nettype none
module spi_timing_guard(input wire clk,rst_n,observe_enable,input wire [7:0] pin_sample,
 input wire [2:0] select_pin,clock_pin,input wire select_active_level,clock_idle_level,sample_trailing,
 input wire [7:0] minimum_half_ticks,minimum_select_ticks,
 output reg timing_observed,timing_safe,timing_violation);
reg [7:0] previous; reg previous_selected; reg [7:0] half_ticks,select_ticks;
reg saw_clock,saw_sample,frame_safe;
wire selected=pin_sample[select_pin]==select_active_level;
wire leading=previous[clock_pin]==clock_idle_level&&pin_sample[clock_pin]!=clock_idle_level;
wire trailing=previous[clock_pin]!=clock_idle_level&&pin_sample[clock_pin]==clock_idle_level;
wire clock_edge=leading||trailing; wire sample_now=selected&&(sample_trailing?trailing:leading);
always @(posedge clk) begin
 if(!rst_n) begin previous<=0;previous_selected<=0;half_ticks<=0;select_ticks<=0;saw_clock<=0;saw_sample<=0;frame_safe<=1;timing_observed<=0;timing_safe<=0;timing_violation<=0;end
 else begin previous<=pin_sample;previous_selected<=selected;
  if(!observe_enable) begin half_ticks<=0;select_ticks<=0;saw_clock<=0;saw_sample<=0;end
  else if(selected&&!previous_selected) begin half_ticks<=0;select_ticks<=0;saw_clock<=0;saw_sample<=0;frame_safe<=1;end
  else if(selected) begin
   if(half_ticks!=8'hff)half_ticks<=half_ticks+1'b1;
   if(!saw_sample&&select_ticks!=8'hff)select_ticks<=select_ticks+1'b1;
   if(clock_edge) begin if(saw_clock&&half_ticks<minimum_half_ticks)begin frame_safe<=0;timing_violation<=1;end half_ticks<=0;saw_clock<=1;end
   if(sample_now&&!saw_sample)begin if(select_ticks<minimum_select_ticks)begin frame_safe<=0;timing_violation<=1;end saw_sample<=1;end
  end else if(!selected&&previous_selected&&saw_sample)begin timing_observed<=1;timing_safe<=frame_safe;end
 end
end
endmodule
`default_nettype wire
