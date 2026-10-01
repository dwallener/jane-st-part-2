import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import make_uart_case


def on_pin(samples: tuple[int, ...], pin: int, invert: bool = False) -> tuple[int, ...]:
    return tuple((((sample & 1) ^ int(invert)) << pin) for sample in samples)


class UartSymbolHypothesisRtlTest(unittest.TestCase):
    def test_uart_candidates_and_multi_pin_refusal(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        fixtures = (
            ("normal", on_pin(make_uart_case(0x55).waveform.samples, 3), 3, 1),
            ("inverted", on_pin(make_uart_case(0xA5).waveform.samples, 6, True), 6, 0),
        )
        body: list[str] = []
        for name, samples, pin, idle in fixtures:
            body.extend(
                [
                    "rst_n=0;observe_enable=0;tick();",
                    f"pin_sample=8'h{samples[0]:02x};rst_n=1;observe_enable=1;tick();",
                    *(f"pin_sample=8'h{sample:02x};tick();" for sample in samples[1:]),
                    "observe_enable=0;tick();while(!ready)tick();#1;",
                    f'if (!candidate_valid || uart_pin != {pin} || idle_level != {idle}) fail("{name}: pin/idle");',
                    f'if (!bit_period_mask[2] || !data_width_mask[3]) fail("{name}: period/width");',
                    f'if (!parity_mask[0] || !stop_count_mask[0]) fail("{name}: framing");',
                ]
            )

        noisy = list(on_pin(make_uart_case(0x55).waveform.samples, 3))
        for index in range(len(noisy) // 2, len(noisy)):
            noisy[index] |= ((index & 1) << 5)
        body.extend(
            [
                "rst_n=0;observe_enable=0;tick();",
                f"pin_sample=8'h{noisy[0]:02x};rst_n=1;observe_enable=1;tick();",
                *(f"pin_sample=8'h{sample:02x};tick();" for sample in noisy[1:]),
                "observe_enable=0;tick();while(!ready)tick();#1;",
                'if (!ready || uart_pin_valid || candidate_valid) fail("multi-pin refusal");',
            ]
        )

        testbench = """
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,observe_enable=0;reg[7:0]pin_sample=0;
wire ready,candidate_valid,candidate_ambiguous,uart_pin_valid,idle_level;
wire[2:0]uart_pin,parity_mask;wire[14:0]bit_period_mask;wire[4:0]data_width_mask;
wire[1:0]stop_count_mask;wire[9:0]candidate_count;wire[8:0]decoded_value;
always#5 clk=~clk;
uart_symbol_hypothesis dut(.*);
task tick;begin @(posedge clk);#1;end endtask
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
""" + "\n".join(body) + """
$display("UART SYMBOL HYPOTHESIS PASS");$finish(0);
end endmodule
"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "uart.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "uart_symbol_hypothesis_seq.v"), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("UART SYMBOL HYPOTHESIS PASS", simulation.stdout)
