import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class RandomizedInterrogationRtlTest(unittest.TestCase):
    """Closed-loop black-box interrogation with scorer-only target truth."""

    def test_random_target_stays_behind_chinese_wall(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        # Reproducible randomized cases. Both candidates cross the DUT boundary;
        # selected_target is used only to parameterize the black-box target and
        # to score the result after simulation.
        rng = random.Random(0x4D494E44)
        for case_index in range(16):
            candidate_a, candidate_b = rng.sample(range(0x08, 0x78), 2)
            selected_target = rng.choice((candidate_a, candidate_b))
            expected_a = int(selected_target == candidate_a)
            with self.subTest(
                case=case_index,
                candidates=(candidate_a, candidate_b),
                selected="A" if expected_a else "B",
            ):
                testbench = self._testbench(
                    candidate_a, candidate_b, selected_target, expected_a
                )
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary = Path(temporary_directory)
                    tb = temporary / "tb.sv"
                    tb.write_text(testbench)
                    output = temporary / "interrogation.vvp"
                    compile_result = subprocess.run(
                        [
                            iverilog,
                            "-g2012",
                            "-s",
                            "tb",
                            "-o",
                            str(output),
                            str(root / "src" / "open_drain_address_probe.v"),
                            str(root / "src" / "two_candidate_i2c_interrogator.v"),
                            str(
                                root
                                / "test"
                                / "interrogation"
                                / "models"
                                / "open_drain_target_model.sv"
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
                    self.assertIn("RANDOMIZED INTERROGATION PASS", simulation.stdout)

    @staticmethod
    def _testbench(
        candidate_a: int,
        candidate_b: int,
        selected_target: int,
        expected_a: int,
    ) -> str:
        return f"""
`timescale 1ns/1ps
`default_nettype none
module tb;
  reg clk=0,rst_n=0,start=0,authorize=0,abort_request=0,candidates_valid=1;
  reg host_scl_low=0,host_sda_low=0;
  localparam [2:0] CLOCK_PIN=3'd2, DATA_PIN=3'd5;
  wire [6:0] candidate_a=7'h{candidate_a:02x};
  wire [6:0] candidate_b=7'h{candidate_b:02x};
  wire [7:0] pin_out,pin_oe,pin_in;
  wire probe_valid,busy,done,resolved,candidate_a_survives;
  wire candidate_b_survives,contradiction,timed_out,revoked;
  wire [6:0] probe_address;

  tri scl;
  tri sda;
  pullup (weak1) scl_pullup(scl);
  pullup (weak1) sda_pullup(sda);
  assign (strong0, highz1) scl = pin_oe[CLOCK_PIN] ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = pin_oe[DATA_PIN] ? 1'b0 : 1'bz;
  assign (strong0, highz1) scl = host_scl_low ? 1'b0 : 1'bz;
  assign (strong0, highz1) sda = host_sda_low ? 1'b0 : 1'bz;
  assign pin_in = {{2'b11,sda,2'b11,scl,2'b11}};

  // SECRET_ADDRESS is confined to this simulation-only target instance.
  open_drain_target_model #(.SECRET_ADDRESS(7'h{selected_target:02x})) target(
      .scl(scl),.sda(sda));

  two_candidate_i2c_interrogator dut(
      .clk(clk),.rst_n(rst_n),.start(start),.authorize(authorize),
      .abort_request(abort_request),
      .candidates_valid(candidates_valid),.candidate_a(candidate_a),
      .candidate_b(candidate_b),.clock_pin(CLOCK_PIN),.data_pin(DATA_PIN),
      .pin_in(pin_in),.pin_out(pin_out),.pin_oe(pin_oe),
      .probe_valid(probe_valid),.probe_address(probe_address),.busy(busy),
      .done(done),.resolved(resolved),
      .candidate_a_survives(candidate_a_survives),
      .candidate_b_survives(candidate_b_survives),
      .contradiction(contradiction),.timed_out(timed_out),.revoked(revoked));

  always #5 clk=~clk;
  always @* begin
    if ((pin_oe & pin_out) != 0) fail("active-high drive requested");
    if ((pin_oe & ~((8'b1<<CLOCK_PIN)|(8'b1<<DATA_PIN))) != 0)
      fail("unrelated pin driven");
  end
  task tick;begin @(posedge clk);#1;end endtask
  task fail;input[8*120-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
  initial begin
    repeat(2)tick();rst_n=1;tick();
    // Proposal is visible while the secret remains confined to the target.
    if(!probe_valid||probe_address!=candidate_a)fail("proposal");

    // Starting without ownership can never touch the bus.
    start=1;tick();start=0;repeat(3)tick();
    if(pin_oe!=0||busy||done)fail("unauthorized start");

    authorize=1;start=1;tick();start=0;
    while(!done)begin tick();if((pin_oe&pin_out)!=0)fail("not open drain");end
    if(!resolved||timed_out||revoked||contradiction)fail("probe did not resolve");
    if(candidate_a_survives!={expected_a}||candidate_b_survives=={expected_a})
      fail("secret target not identified");
    if(pin_oe!=0)fail("completion did not release bus");

    // A host that revokes the grant forces combinational release.
    start=1;tick();start=0;repeat(3)tick();
    authorize=0;#1;if(pin_oe!=0)fail("revocation release");
    tick();while(!done)tick();if(!revoked)fail("revocation not reported");

    // A stuck-low clock is an electrical/front-end failure, not a NACK.
    rst_n=0;tick();rst_n=1;authorize=1;host_scl_low=1;start=1;tick();start=0;
    while(!done)tick();
    if(!timed_out||resolved||pin_oe!=0)fail("stuck clock timeout");
    host_scl_low=0;
    $display("RANDOMIZED INTERROGATION PASS");$finish(0);
  end
endmodule
`default_nettype wire
"""
