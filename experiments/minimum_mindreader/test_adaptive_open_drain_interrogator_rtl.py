import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class AdaptiveOpenDrainInterrogatorRtlTest(unittest.TestCase):
    def test_passive_equivalence_is_resolved_through_wire_probes(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        secrets = list(range(7))
        random.Random(0x4348494E41).shuffle(secrets)
        first_probes: set[int] = set()
        for secret_bit in secrets:
            with self.subTest(secret_bit=secret_bit):
                testbench = self._testbench(secret_bit)
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary = Path(temporary_directory)
                    tb = temporary / "tb.sv"
                    tb.write_text(testbench)
                    output = temporary / "adaptive.vvp"
                    compile_result = subprocess.run(
                        [
                            iverilog,
                            "-g2012",
                            "-s",
                            "tb",
                            "-o",
                            str(output),
                            str(root / "src" / "open_drain_bit_learner.v"),
                            str(root / "src" / "open_drain_address_probe.v"),
                            str(root / "src" / "adaptive_open_drain_interrogator.v"),
                            str(
                                root
                                / "test"
                                / "interrogation"
                                / "models"
                                / "open_drain_bit_target_model.sv"
                            ),
                            str(tb),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        compile_result.returncode, 0, compile_result.stderr
                    )
                    simulation = subprocess.run(
                        [vvp, str(output)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        simulation.returncode,
                        0,
                        simulation.stdout + simulation.stderr,
                    )
                    self.assertIn("ADAPTIVE OPEN DRAIN PASS", simulation.stdout)
                    first_line = next(
                        line for line in simulation.stdout.splitlines()
                        if line.startswith("FIRST_PROBE=")
                    )
                    first_probes.add(int(first_line.split("=", 1)[1], 16))

        # The proposal is a function of public evidence, never the hidden bit.
        self.assertEqual(len(first_probes), 1)

    @staticmethod
    def _testbench(secret_bit: int) -> str:
        return f"""
`timescale 1ns/1ps
`default_nettype none
module tb;
  reg clk=0,rst_n=0,passive_observation_valid=0,passive_ack=0;
  reg[6:0]passive_request=0;
  reg start=0,authorize=0,abort_request=0;
  localparam[2:0]CLOCK_PIN=3'd2,DATA_PIN=3'd5;
  wire[7:0]pin_in,pin_out,pin_oe;
  wire proposal_valid,busy,probe_done,resolved,contradiction,timed_out,revoked;
  wire[6:0]proposal_request;wire[4:0]candidate_count;
  wire winner_invert;wire[2:0]winner_bit;
  integer probe_count=0,search_cycles=0;reg[6:0]first_probe=0;

  tri scl;tri sda;
  pullup(weak1)scl_pullup(scl);pullup(weak1)sda_pullup(sda);
  assign(strong0,highz1)scl=pin_oe[CLOCK_PIN]?1'b0:1'bz;
  assign(strong0,highz1)sda=pin_oe[DATA_PIN]?1'b0:1'bz;
  assign pin_in={{2'b11,sda,2'b11,scl,2'b11}};

  // SECRET_BIT is present only in the simulation target, never a DUT input.
  open_drain_bit_target_model #(.SECRET_BIT({secret_bit})) target(.scl(scl),.sda(sda));
  adaptive_open_drain_interrogator dut(
      .clk(clk),.rst_n(rst_n),
      .passive_observation_valid(passive_observation_valid),
      .passive_request(passive_request),.passive_ack(passive_ack),
      .start(start),.authorize(authorize),.abort_request(abort_request),
      .clock_pin(CLOCK_PIN),.data_pin(DATA_PIN),.pin_in(pin_in),
      .pin_out(pin_out),.pin_oe(pin_oe),.proposal_valid(proposal_valid),
      .proposal_request(proposal_request),.busy(busy),.probe_done(probe_done),
      .resolved(resolved),.contradiction(contradiction),.timed_out(timed_out),
      .revoked(revoked),.candidate_count(candidate_count),
      .winner_invert(winner_invert),.winner_bit(winner_bit));

  always#5 clk=~clk;
  always@*begin
    if((pin_oe&pin_out)!=0)fail("active high");
    if((pin_oe&~((8'b1<<CLOCK_PIN)|(8'b1<<DATA_PIN)))!=0)fail("wrong pin");
  end
  task tick;begin @(posedge clk);#1;end endtask
  task observe;input[6:0]request;input ack;begin
    passive_request=request;passive_ack=ack;passive_observation_valid=1;tick();
    passive_observation_valid=0;tick();
  end endtask
  task fail;input[8*120-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
  initial begin
    repeat(2)tick();rst_n=1;tick();
    // These observations are identical for every possible secret bit.
    observe(7'h00,1'b0);observe(7'h7f,1'b1);
    if(candidate_count!=7||resolved)fail("passive ambiguity");
    while(!proposal_valid)begin
      tick();search_cycles=search_cycles+1;
      if(search_cycles>130)fail("proposal search timeout");
    end
    first_probe=proposal_request;$display("FIRST_PROBE=%02x",first_probe);
    authorize=1;
    while(!resolved)begin
      if(!proposal_valid)fail("no distinguishing proposal");
      start=1;tick();start=0;
      while(!probe_done)tick();
      if(timed_out||revoked||contradiction)fail("probe fault");
      probe_count=probe_count+1;
      tick();
      if(probe_count>3)fail("probe budget");
      search_cycles=0;
      while(!resolved&&!proposal_valid)begin
        tick();search_cycles=search_cycles+1;
        if(search_cycles>130)fail("proposal rescan timeout");
      end
    end
    if(winner_invert||winner_bit!={secret_bit})fail("wrong hidden behavior");
    if(pin_oe!=0)fail("bus not released");
    $display("ADAPTIVE OPEN DRAIN PASS");$finish(0);
  end
endmodule
`default_nettype wire
"""
