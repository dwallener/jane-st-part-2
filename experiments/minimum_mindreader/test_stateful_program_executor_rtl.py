import shutil,subprocess,tempfile,unittest
from pathlib import Path
from model import BitExpression,ExpressionKind
from protocol_program import GuardedTransition,ProtocolProgram

def bits(kind):return tuple(BitExpression(kind,i) for i in range(8))
def const(v):return tuple(BitExpression(ExpressionKind.CONSTANT,(v>>i)&1) for i in range(8))
class Test(unittest.TestCase):
 def test_state(self):
  p=ProtocolProgram((GuardedTransition(0,255,0x55,const(0xaa),0,1),GuardedTransition(0,240,0xa0,bits(ExpressionKind.COPY),0,0),GuardedTransition(1,255,0x55,const(0xaa),0,0),GuardedTransition(1,240,0xa0,bits(ExpressionKind.INVERT),0,1)))
  data=p.encode();loads=''.join(f'mem[{i}]=8\'h{x:02x};' for i,x in enumerate(data));iv=shutil.which('iverilog');vv=shutil.which('vvp');self.assertTrue(iv and vv);r=Path(__file__).resolve().parents[2]
  tb=f'''`timescale 1ns/1ps
module tb;reg clk=0,rst_n=0,load_valid=0,load_commit=0,request_valid=0;reg[5:0]load_address;reg[7:0]load_data,request_value,mem[0:39];reg[2:0]load_transition_count=4;wire model_valid,response_valid,unknown;wire[7:0]response_value;wire[3:0]current_state;integer i;always#5 clk=~clk;stateful_program_executor d(.*);task tick;begin @(posedge clk);#1;end endtask task req;input[7:0]x;begin request_value=x;request_valid=1;tick();request_valid=0;end endtask task fail;input[399:0]s;begin $display("FAIL %0s",s);$finish(1);end endtask initial begin {loads} repeat(2)tick();rst_n=1;for(i=0;i<40;i=i+1)begin load_address=i;load_data=mem[i];load_valid=1;tick();end load_valid=0;load_commit=1;tick();load_commit=0;if(!model_valid)fail("load");req(8'ha7);if(!response_valid||response_value!=8'ha7||current_state!=0)fail("s0");req(8'h55);if(response_value!=8'haa||current_state!=1)fail("toggle");req(8'ha7);if(response_value!=8'h58||current_state!=1)fail("s1");req(8'hb7);if(!unknown||current_state!=1)fail("unknown mutation");$display("STATEFUL EXECUTOR PASS");$finish(0);end endmodule'''
  with tempfile.TemporaryDirectory() as d:
   t=Path(d)/'t.v';t.write_text(tb);o=Path(d)/'x';c=subprocess.run([iv,'-g2012','-s','tb','-o',str(o),str(r/'src/stateful_program_executor.v'),str(t)],capture_output=True,text=True);self.assertEqual(c.returncode,0,c.stderr);s=subprocess.run([vv,str(o)],capture_output=True,text=True);self.assertEqual(s.returncode,0,s.stdout+s.stderr);self.assertIn('STATEFUL EXECUTOR PASS',s.stdout)
