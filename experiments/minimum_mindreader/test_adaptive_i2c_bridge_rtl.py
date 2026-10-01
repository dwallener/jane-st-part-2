import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class AdaptiveI2cBridgeRtlTest(unittest.TestCase):
    def test_raw_passive_frames_lead_to_adaptive_wire_probes(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        secrets = list(range(7))
        random.Random(0x425249444745).shuffle(secrets)
        first_probes: set[int] = set()
        for secret_bit in secrets:
            with self.subTest(secret_bit=secret_bit):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary = Path(temporary_directory)
                    tb = temporary / "tb.sv"
                    tb.write_text(self._testbench(secret_bit))
                    output = temporary / "bridge.vvp"
                    compile_result = subprocess.run(
                        [
                            iverilog, "-g2012", "-s", "tb", "-o", str(output),
                            str(root / "src" / "i2c_symbol_hypothesis.v"),
                            str(root / "src" / "open_drain_bit_learner.v"),
                            str(root / "src" / "open_drain_address_probe.v"),
                            str(root / "src" / "adaptive_open_drain_interrogator.v"),
                            str(root / "src" / "adaptive_i2c_interrogation_bridge.v"),
                            str(root / "test" / "interrogation" / "models" /
                                "open_drain_bit_target_model.sv"),
                            str(tb),
                        ],
                        check=False, capture_output=True, text=True,
                    )
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stderr)
                    simulation = subprocess.run(
                        [vvp, str(output)], check=False,
                        capture_output=True, text=True,
                    )
                    self.assertEqual(simulation.returncode, 0,
                                     simulation.stdout + simulation.stderr)
                    self.assertIn("ADAPTIVE I2C BRIDGE PASS", simulation.stdout)
                    first_line = next(
                        line for line in simulation.stdout.splitlines()
                        if line.startswith("FIRST_PROBE=")
                    )
                    first_probes.add(int(first_line.split("=", 1)[1], 16))

        self.assertEqual(len(first_probes), 1)

    @staticmethod
    def _testbench(secret_bit: int) -> str:
        return f"""
`timescale 1ns/1ps
`default_nettype none
module tb;
  reg clk=0,rst_n=0,observe_enable=0,start=0,authorize=0,abort_request=0;
  reg host_scl_low=0,host_sda_low=0;
  localparam[2:0]CLOCK_PIN=3'd2,DATA_PIN=3'd5;
  wire[7:0]pin_in,pin_out,pin_oe;
  wire passive_ready,passive_accepted,proposal_valid,busy,probe_done;
  wire resolved,contradiction,timed_out,revoked,winner_invert;
  wire[6:0]proposal_request;wire[4:0]candidate_count;
  wire[2:0]winner_bit,inferred_clock_pin,inferred_data_pin;
  integer probe_count=0,wait_count=0;reg[6:0]first_probe=0;

  tri scl;tri sda;
  pullup(weak1)scl_pullup(scl);pullup(weak1)sda_pullup(sda);
  assign(strong0,highz1)scl=host_scl_low?1'b0:1'bz;
  assign(strong0,highz1)sda=host_sda_low?1'b0:1'bz;
  assign(strong0,highz1)scl=pin_oe[CLOCK_PIN]?1'b0:1'bz;
  assign(strong0,highz1)sda=pin_oe[DATA_PIN]?1'b0:1'bz;
  assign pin_in={{2'b11,sda,2'b11,scl,2'b11}};

  open_drain_bit_target_model #(.SECRET_BIT({secret_bit})) target(.scl(scl),.sda(sda));
  adaptive_i2c_interrogation_bridge dut(
      .clk(clk),.rst_n(rst_n),.observe_enable(observe_enable),
      .start(start),.authorize(authorize),.abort_request(abort_request),
      .pin_in(pin_in),.pin_out(pin_out),.pin_oe(pin_oe),
      .passive_ready(passive_ready),.passive_accepted(passive_accepted),
      .proposal_valid(proposal_valid),.proposal_request(proposal_request),
      .busy(busy),.probe_done(probe_done),.resolved(resolved),
      .contradiction(contradiction),.timed_out(timed_out),.revoked(revoked),
      .candidate_count(candidate_count),.winner_invert(winner_invert),
      .winner_bit(winner_bit),.inferred_clock_pin(inferred_clock_pin),
      .inferred_data_pin(inferred_data_pin));

  always#5 clk=~clk;
  always@*begin
    if((pin_oe&pin_out)!=0)fail("active high");
    if((pin_oe&~((8'b1<<CLOCK_PIN)|(8'b1<<DATA_PIN)))!=0)fail("wrong pin");
  end
  task tick;begin @(posedge clk);#1;end endtask
  task lines;input scl_low;input sda_low;begin
    host_scl_low=scl_low;host_sda_low=sda_low;tick();
  end endtask
  task passive_frame;input[7:0]value;integer bit_no;begin
    observe_enable=1;lines(0,0);lines(0,1);
    for(bit_no=7;bit_no>=0;bit_no=bit_no-1)begin
      lines(1,!value[bit_no]);lines(0,!value[bit_no]);lines(1,!value[bit_no]);
    end
    lines(1,0);lines(0,0);lines(1,0);
    lines(1,1);lines(0,1);lines(0,0);
    observe_enable=0;tick();tick();tick();
  end endtask
  task fail;input[8*120-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
  initial begin
    repeat(2)tick();rst_n=1;tick();
    passive_frame(8'h00);
    passive_frame(8'hfe);
    if(candidate_count!=7||resolved)fail("raw passive ambiguity");
    if(inferred_clock_pin!=CLOCK_PIN||inferred_data_pin!=DATA_PIN)fail("roles");
    while(!proposal_valid)begin tick();wait_count=wait_count+1;
      if(wait_count>130)fail("proposal timeout");end
    first_probe=proposal_request;$display("FIRST_PROBE=%02x",first_probe);
    authorize=1;
    while(!resolved)begin
      start=1;tick();start=0;
      while(!probe_done)tick();
      if(timed_out||revoked||contradiction)fail("probe fault");
      probe_count=probe_count+1;tick();wait_count=0;
      while(!resolved&&!proposal_valid)begin tick();wait_count=wait_count+1;
        if(wait_count>130)fail("rescan timeout");end
      if(probe_count>3)fail("probe budget");
    end
    if(winner_invert||winner_bit!={secret_bit})fail("wrong hidden behavior");
    if(pin_oe!=0)fail("bus not released");
    $display("ADAPTIVE I2C BRIDGE PASS");$finish(0);
  end
endmodule
`default_nettype wire
"""
