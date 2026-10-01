import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import make_i2c_write_case, make_spi_case, make_uart_case


def remap(samples: tuple[int, ...], mapping: tuple[int, ...]) -> tuple[int, ...]:
    result = []
    for sample in samples:
        physical = 0
        for local_pin, physical_pin in enumerate(mapping):
            physical |= ((sample >> local_pin) & 1) << physical_pin
        result.append(physical)
    return tuple(result)


class SerialHypothesisRouterRtlTest(unittest.TestCase):
    def test_structural_routes_are_nonexclusive_and_honest(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        cases = (
            (
                "selected synchronous",
                remap(make_spi_case(1, True).waveform.samples, (6, 1, 7, 4)),
                0b011,
            ),
            (
                "asynchronous single wire",
                remap(make_uart_case(0x55).waveform.samples, (3,)),
                0b001,
            ),
            (
                "shared two wire",
                remap(make_i2c_write_case().waveform.samples, (2, 5)),
                0b101,
            ),
            ("quiet insufficient", (0,) * 20, 0b000),
        )

        body: list[str] = []
        for name, samples, expected in cases:
            body.extend(
                [
                    "rst_n=0; observe_enable=0; tick();",
                    f"pin_sample=8'h{samples[0]:02x}; rst_n=1; observe_enable=1; tick();",
                    *(f"pin_sample=8'h{sample:02x}; tick();" for sample in samples[1:]),
                    "observe_enable=0; tick(); #1;",
                    f'if (!ready || candidate_classes != 3\'b{expected:03b}) fail("{name}: classes");',
                    f'if (ambiguous != {1 if expected in (0b011, 0b101) else 0}) fail("{name}: ambiguity");',
                    f'if (insufficient != {1 if expected == 0 else 0}) fail("{name}: insufficiency");',
                ]
            )

        testbench = """
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,observe_enable=0; reg[7:0]pin_sample=0;
    wire ready,insufficient,ambiguous,evidence_saturated; wire[7:0]activity_mask,async_candidate_mask,clock_candidate_mask,select_candidate_mask; wire[2:0]candidate_classes;
always#5 clk=~clk;
serial_hypothesis_router dut(.*);
task tick;begin @(posedge clk);#1;end endtask
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
""" + "\n".join(body) + """
$display("SERIAL HYPOTHESIS ROUTER PASS");$finish(0);
end endmodule
"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "router.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "tb",
                    "-o",
                    str(output),
                    str(root / "src" / "serial_hypothesis_router.v"),
                    str(tb),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("SERIAL HYPOTHESIS ROUTER PASS", simulation.stdout)
