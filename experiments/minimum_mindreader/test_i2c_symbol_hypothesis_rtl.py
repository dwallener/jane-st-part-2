import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import make_i2c_write_case


def remap(samples: tuple[int, ...], clock_pin: int, data_pin: int) -> tuple[int, ...]:
    return tuple(
        (((sample >> 0) & 1) << clock_pin)
        | (((sample >> 1) & 1) << data_pin)
        for sample in samples
    )


class I2cSymbolHypothesisRtlTest(unittest.TestCase):
    def test_online_role_frame_and_ack_inference(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]
        samples = remap(make_i2c_write_case().waveform.samples, 2, 5)
        truncated = samples[:-1]

        drives = "\n".join(f"pin_sample=8'h{x:02x};tick();" for x in samples[1:])
        truncated_drives = "\n".join(
            f"pin_sample=8'h{x:02x};tick();" for x in truncated[1:]
        )
        testbench = f"""
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,observe_enable=0;reg[7:0]pin_sample=0;
wire ready,candidate_valid,candidate_ambiguous,open_drain_required;
wire[5:0]candidate_count;wire[7:0]clock_candidate_mask,data_candidate_mask;
wire[2:0]clock_pin,data_pin;wire[7:0]first_byte,second_byte;
wire[1:0]ack_bits,decoded_byte_count;
always#5 clk=~clk;
i2c_symbol_hypothesis dut(.*);
task tick;begin @(posedge clk);#1;end endtask
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
rst_n=0;tick();pin_sample=8'h{samples[0]:02x};rst_n=1;observe_enable=1;tick();
{drives}
observe_enable=0;tick();#1;
if(!ready||!candidate_valid||candidate_ambiguous||candidate_count!=1)fail("unique");
if(clock_pin!=2||data_pin!=5)fail("roles");
if(first_byte!=8'ha0||second_byte!=8'h2a||ack_bits!=0||decoded_byte_count!=2)fail("decode");
if(!open_drain_required)fail("open drain");
rst_n=0;observe_enable=0;tick();pin_sample=8'h{truncated[0]:02x};rst_n=1;observe_enable=1;tick();
{truncated_drives}
observe_enable=0;tick();#1;
if(!ready||candidate_valid||candidate_count!=0)fail("missing stop refusal");
$display("I2C SYMBOL HYPOTHESIS PASS");$finish(0);
end endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "i2c.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "i2c_symbol_hypothesis.v"), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("I2C SYMBOL HYPOTHESIS PASS", simulation.stdout)
