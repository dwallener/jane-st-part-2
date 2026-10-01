`default_nettype none
module active_probe_controller(input wire clk,rst_n,restart,input wire[7:0]request_mask,request_value,
 input wire[143:0]candidate_a,candidate_b,input wire candidates_distinct,authorize,
 input wire observation_valid,input wire[7:0]observed_response,
 output reg probe_valid,output reg[7:0]probe_request,output reg transmit,
 output reg candidate_a_survives,candidate_b_survives,observation_resolved,observation_contradiction);
reg[7:0]scan_request;reg scanning,transmitted;integer bit_index,expression_index;reg[7:0]response_a,response_b,probe_response_a,probe_response_b;
function eval_bit;input[143:0]m;input[7:0]r;input integer b;integer e;begin eval_bit=0;for(e=0;e<18;e=e+1)if(m[b*18+e])begin if(e==1)eval_bit=1;else if(e>=2)begin eval_bit=r[(e-2)>>1];if(e[0])eval_bit=~eval_bit;end end end endfunction
always @* begin response_a=0;response_b=0;for(bit_index=0;bit_index<8;bit_index=bit_index+1)begin response_a[bit_index]=eval_bit(candidate_a,scan_request,bit_index);response_b[bit_index]=eval_bit(candidate_b,scan_request,bit_index);end end
always @(posedge clk)begin
 if(!rst_n||restart)begin scan_request<=0;scanning<=candidates_distinct;probe_valid<=0;probe_request<=0;transmit<=0;transmitted<=0;probe_response_a<=0;probe_response_b<=0;candidate_a_survives<=1;candidate_b_survives<=1;observation_resolved<=0;observation_contradiction<=0;end
 else begin transmit<=0;
  if(scanning)begin
   if(((scan_request&request_mask)==request_value)&&(response_a!=response_b))begin probe_valid<=1;probe_request<=scan_request;probe_response_a<=response_a;probe_response_b<=response_b;scanning<=0;end
   else if(scan_request==8'hff)scanning<=0;else scan_request<=scan_request+1'b1;
  end
  if(authorize&&probe_valid&&!transmitted)begin transmit<=1;transmitted<=1;end
  if(observation_valid&&transmitted&&probe_valid&&!observation_resolved&&!observation_contradiction)begin
   candidate_a_survives<=observed_response==probe_response_a;
   candidate_b_survives<=observed_response==probe_response_b;
   observation_resolved<=(observed_response==probe_response_a)^(observed_response==probe_response_b);
   observation_contradiction<=(observed_response!=probe_response_a)&&(observed_response!=probe_response_b);
  end
 end
end
endmodule
`default_nettype wire
