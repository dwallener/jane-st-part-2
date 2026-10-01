`default_nettype none
module mindreader_status(input wire[3:0]address,input wire[2:0]supervisor_state,fault_reason,
 input wire physical_complete,direction_resolved,model_valid,stream_causal,timing_safe,ownership_granted,
 input wire[7:0]evidence_count,input wire[15:0]survivor_count,input wire[2:0]probe_kind,
 input wire trace_overflow,contradiction,contention,output reg[7:0]data);
always @* case(address)
0:data={5'b0,supervisor_state};1:data={5'b0,fault_reason};
2:data={physical_complete,direction_resolved,model_valid,stream_causal,timing_safe,ownership_granted,contradiction,contention};
3:data=evidence_count;4:data=survivor_count[7:0];5:data=survivor_count[15:8];
6:data={5'b0,probe_kind};7:data={7'b0,trace_overflow};default:data=8'hff;endcase
endmodule
`default_nettype wire
