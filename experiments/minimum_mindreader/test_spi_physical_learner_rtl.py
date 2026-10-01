import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import make_spi_case


def remap_sample(sample: int, old_to_new: tuple[int, ...]) -> int:
    result = 0
    for old_pin, new_pin in enumerate(old_to_new):
        result |= ((sample >> old_pin) & 1) << new_pin
    return result


class SpiPhysicalLearnerRtlTest(unittest.TestCase):
    def test_all_modes_orders_and_permuted_pins(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        fixtures: list[tuple[str, tuple[int, ...], int, int, tuple[int, int]]] = []
        for mode in range(4):
            for msb_first in (True, False):
                case = make_spi_case(mode, msb_first)
                fixtures.append(
                    (
                        case.name,
                        case.waveform.samples,
                        mode,
                        3,
                        (1, 2),
                    )
                )
        permutation = (6, 1, 7, 4)
        case = make_spi_case(3, True)
        fixtures.append(
            (
                "permuted",
                tuple(remap_sample(sample, permutation) for sample in case.waveform.samples),
                3,
                permutation[3],
                tuple(sorted((permutation[1], permutation[2]))),
            )
        )

        body: list[str] = []
        for name, samples, mode, select_pin, data_pins in fixtures:
            clock_pin = 0 if name != "permuted" else permutation[0]
            body.extend(
                [
                    "rst_n = 0; capture_enable = 0; tick();",
                    f"pin_sample = 8'h{samples[0]:x}; rst_n = 1; capture_enable = 1; tick();",
                    *(f"pin_sample = 8'h{sample:x}; tick();" for sample in samples[1:]),
                    "capture_enable = 0; tick(); #1;",
                    f'if (!physical_complete || candidate_count != 1) fail("{name}: unresolved");',
                    f'if (select_pin != {select_pin} || clock_pin != {clock_pin}) fail("{name}: roles");',
                    f'if (data_a_pin != {data_pins[0]} || data_b_pin != {data_pins[1]}) fail("{name}: data pins");',
                    f'if (select_active_level != 0 || clock_idle_level != {mode >> 1}) fail("{name}: levels");',
                    f'if (sample_trailing != {mode & 1}) fail("{name}: edge");',
                ]
            )

        ambiguous = tuple(sample & ~(1 << 2) for sample in make_spi_case(1, True).waveform.samples)
        body.extend(
            [
                "rst_n = 0; capture_enable = 0; tick();",
                f"pin_sample = 8'h{ambiguous[0]:x}; rst_n = 1; capture_enable = 1; tick();",
                *(f"pin_sample = 8'h{sample:x}; tick();" for sample in ambiguous[1:]),
                "capture_enable = 0; tick(); #1;",
                'if (!ready || physical_complete || data_candidate_count != 1) fail("constant data ambiguity");',
            ]
        )

        noisy = tuple(sample ^ (((index & 1) << 5))
                      for index, sample in enumerate(make_spi_case(1, True).waveform.samples))
        body.extend(
            [
                "rst_n = 0; capture_enable = 0; tick();",
                f"pin_sample = 8'h{noisy[0]:x}; rst_n = 1; capture_enable = 1; tick();",
                *(f"pin_sample = 8'h{sample:x}; tick();" for sample in noisy[1:]),
                "capture_enable = 0; tick(); #1;",
                'if (!ready || physical_complete || data_candidate_count < 3) fail("extra active pin ambiguity");',
            ]
        )

        testbench = """
`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, capture_enable=0; reg [7:0] pin_sample=0;
wire ready, physical_complete; wire [2:0] select_pin,clock_pin,data_a_pin,data_b_pin;
wire select_active_level,clock_idle_level,sample_trailing; wire [5:0] candidate_count;
wire [7:0] data_candidate_mask; wire [3:0] data_candidate_count;
always #5 clk=~clk;
spi_physical_learner dut(.*);
task tick; begin @(posedge clk); #1; end endtask
task fail; input [8*100-1:0] m; begin $display("FAIL: %0s",m); $finish(1); end endtask
initial begin
""" + "\n".join(body) + """
$display("SPI PHYSICAL LEARNER PASS"); $finish(0);
end
endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "physical.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "spi_physical_learner.v"), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(simulation.returncode, 0, simulation.stdout + simulation.stderr)
            self.assertIn("SPI PHYSICAL LEARNER PASS", simulation.stdout)
