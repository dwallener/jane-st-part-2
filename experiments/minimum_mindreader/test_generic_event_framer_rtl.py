import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class GenericEventFramerRtlTest(unittest.TestCase):
    def test_nonexclusive_online_frame_evidence(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        testbench = r"""
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,observe_enable=0;reg[7:0]pin_sample=0;
    wire ready,ambiguous,insufficient,evidence_saturated;wire[2:0]candidate_classes;
wire[7:0]control_candidate_mask,first_burst_events,latest_burst_events;
wire[3:0]burst_count;
always#5 clk=~clk;
generic_event_framer dut(.*);
task tick;begin @(posedge clk);#1;end endtask
task sample;input[7:0]v;begin pin_sample=v;tick();end endtask
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
// Pin 4 encloses activity with exactly two transitions.
rst_n=0;tick();rst_n=1;observe_enable=1;sample(8'h10);
sample(8'h00);sample(8'h01);sample(8'h00);sample(8'h02);sample(8'h00);sample(8'h10);
observe_enable=0;tick();#1;
if(!ready||!candidate_classes[0]||control_candidate_mask!=8'h10)fail("control enclosure");

// Two equal four-event bursts separated by a quiet gap retain gap and fixed-count.
rst_n=0;tick();rst_n=1;observe_enable=1;sample(0);sample(1);sample(0);sample(1);sample(0);
repeat(5)sample(0);sample(1);sample(0);sample(1);sample(0);
observe_enable=0;tick();#1;
if(!candidate_classes[1]||!candidate_classes[2]||!ambiguous)fail("equal bursts");
if(first_burst_events!=4||latest_burst_events!=4||burst_count!=2)fail("burst counts");

// A shorter second burst preserves gap framing but eliminates fixed count.
rst_n=0;tick();rst_n=1;observe_enable=1;sample(0);sample(1);sample(0);sample(1);sample(0);
repeat(5)sample(0);sample(1);sample(0);
observe_enable=0;tick();#1;
if(!candidate_classes[1]||candidate_classes[2])fail("unequal bursts");
$display("GENERIC EVENT FRAMER PASS");$finish(0);
end endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "framer.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "generic_event_framer.v"), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("GENERIC EVENT FRAMER PASS", simulation.stdout)
