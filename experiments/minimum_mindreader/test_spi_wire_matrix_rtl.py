import shutil, subprocess, tempfile, unittest
from pathlib import Path
from hierarchical_model import HierarchicalSpiModel,SpiPhysicalModel,build_hierarchical_spi_model
from known_protocol_corpus import make_spi_case
from spi_behavior import make_spi_behavior_corpus

def remap(v,m):
 r=0
 for old,new in enumerate(m):r|=((v>>old)&1)<<new
 return r

class Test(unittest.TestCase):
 def test_modes_orders_and_remap(self):
  iv=shutil.which('iverilog');vv=shutil.which('vvp');self.assertTrue(iv and vv);root=Path(__file__).resolve().parents[2]
  fixtures=[]
  for mode in range(4):
   for order in (True,False):
    case=make_spi_case(mode,order,request=0xA7,response=0x63);model=build_hierarchical_spi_model(make_spi_behavior_corpus(mode,order));fixtures.append((f'm{mode}_{order}',case.waveform.samples,model,0,1,2,3))
  perm=(2,0,3,1);case=make_spi_case(3,True,request=0xA7,response=0x63);base=build_hierarchical_spi_model(make_spi_behavior_corpus(3,True));p=base.physical
  physical=SpiPhysicalModel(perm[p.select_pin],perm[p.clock_pin],perm[p.request_pin],perm[p.response_pin],p.select_active_level,p.clock_idle_level,p.sampling_edge,p.word_bits)
  fixtures.append(('permuted',tuple(remap(x,perm) for x in case.waveform.samples),HierarchicalSpiModel(physical,base.program,base.provenance,base.bit_reverse_equivalent),perm[0],perm[1],perm[2],perm[3]))
  for name,samples,model,clock,request,response,select in fixtures:
   b=model.encode(); lines=[f'artifact[{i}]=8\'h{x:02x};' for i,x in enumerate(b)]
   lines += ['repeat(2)tick();rst_n=1;']
   lines += ['for(i=0;i<22;i=i+1)begin @(negedge clk);load_address=i;load_data=artifact[i];load_valid=1;end','@(negedge clk);load_valid=0;load_commit=1;@(negedge clk);load_commit=0;#1;if(!model_valid||!stream_causal)fail("load");']
   prev=samples[0];sampled=0
   lines.append(f'pin_in=4\'h{prev & ~(1<<response):x};tick();')
   idle=model.physical.clock_idle_level; trailing=model.physical.sampling_edge.value=='trailing'
   for sample in samples[1:]:
    wire=sample&~(1<<response);pc=(prev>>clock)&1;c=(sample>>clock)&1;sel=((sample>>select)&1)==model.physical.select_active_level
    leading=pc==idle and c!=idle;trail=pc!=idle and c==idle;sampling=sel and (trail if trailing else leading)
    lines.append(f'pin_in=4\'h{wire:x};#1;')
    if sampling:
     expected=(sample>>response)&1;lines.append(f'if(pin_oe!=4\'h{1<<response:x}||pin_out[{response}]!={expected})fail("bit{sampled}");');sampled+=1
    lines.append('tick();');prev=sample
   lines.append('if(pin_oe!=0)fail("release");$display("PASS");$finish(0);')
   tb='''`timescale 1ns/1ps
module tb;reg clk=0,rst_n=0,load_valid=0,load_commit=0,request_valid=0;reg[4:0]load_address;reg[7:0]load_data,request_value;reg[3:0]pin_in;wire model_valid,load_error,stream_causal,transfer_valid,transfer_unknown;wire[3:0]pin_out,pin_oe;wire[7:0]transfer_request;reg[7:0]artifact[0:21];integer i;always#5 clk=~clk;spi_model_peripheral dut(.*);task tick;begin @(posedge clk);#1;end endtask task fail;input[799:0]s;begin $display("FAIL %0s",s);$finish(1);end endtask initial begin
'''+''.join(lines)+'\nend endmodule'
   with tempfile.TemporaryDirectory() as td:
    t=Path(td)/'t.v';t.write_text(tb);o=Path(td)/'x';c=subprocess.run([iv,'-g2012','-s','tb','-o',str(o),str(root/'src/hierarchical_model_executor.v'),str(root/'src/spi_model_peripheral.v'),str(t)],capture_output=True,text=True);self.assertEqual(c.returncode,0,name+c.stderr);s=subprocess.run([vv,str(o)],capture_output=True,text=True);self.assertEqual(s.returncode,0,name+s.stdout+s.stderr);self.assertIn('PASS',s.stdout);self.assertEqual(sampled,8)
