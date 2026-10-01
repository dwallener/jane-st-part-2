`default_nettype none
module stateful_program_executor(
 input wire clk,rst_n,load_valid,input wire[5:0]load_address,input wire[7:0]load_data,
 input wire[2:0]load_transition_count,input wire load_commit,
 input wire request_valid,input wire[7:0]request_value,
 output reg model_valid,response_valid,unknown,output reg[7:0]response_value,
 output reg[3:0]current_state);
reg[7:0]memory[0:39];reg[2:0]transition_count;
integer commit_index,commit_base,eval_index,eval_bit,eval_base,match_count,expression_code,reset_index;
reg[39:0]expression_pack;reg[7:0]evaluated;reg[3:0]matched_next;reg commit_ok;
always @* begin
 commit_ok=load_transition_count>0&&load_transition_count<=4;
 for(commit_index=0;commit_index<4;commit_index=commit_index+1)begin commit_base=commit_index*10;if(commit_index<load_transition_count&&(memory[commit_base+8]!=0||memory[commit_base+9]!=0))commit_ok=0;end
end
always @* begin
 match_count=0;evaluated=0;matched_next=current_state;expression_pack=0;
 eval_index=0;eval_bit=0;eval_base=0;expression_code=0;
 for(eval_index=0;eval_index<4;eval_index=eval_index+1)begin
  eval_base=eval_index*10;
  if(eval_index<transition_count&&(memory[eval_base]>>4)==current_state&&((request_value&memory[eval_base+1])==memory[eval_base+2]))begin
   match_count=match_count+1;matched_next=memory[eval_base]&15;expression_pack={memory[eval_base+7],memory[eval_base+6],memory[eval_base+5],memory[eval_base+4],memory[eval_base+3]};
   for(eval_bit=0;eval_bit<8;eval_bit=eval_bit+1)begin expression_code=(expression_pack>>(eval_bit*5))&31;if(expression_code==1)evaluated[eval_bit]=1;else if(expression_code>=2)begin evaluated[eval_bit]=request_value[(expression_code-2)>>1];if(expression_code[0])evaluated[eval_bit]=~evaluated[eval_bit];end else evaluated[eval_bit]=0;end
  end
 end
end
always @(posedge clk)begin
 if(!rst_n)begin model_valid<=0;response_valid<=0;unknown<=0;response_value<=0;current_state<=0;transition_count<=0;for(reset_index=0;reset_index<40;reset_index=reset_index+1)memory[reset_index]<=0;end
 else begin response_valid<=0;unknown<=0;if(load_valid&&load_address<40)memory[load_address]<=load_data;if(load_commit)begin model_valid<=commit_ok;transition_count<=load_transition_count;current_state<=0;end else if(request_valid)begin if(!model_valid||match_count!=1)unknown<=1;else begin response_value<=evaluated;response_valid<=1;current_state<=matched_next;end end end
end
endmodule
`default_nettype wire
