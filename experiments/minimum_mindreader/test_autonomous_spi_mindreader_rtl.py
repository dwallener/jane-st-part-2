import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import make_spi_case
from spi_behavior import TRAINING_REQUESTS, lossy_response


class AutonomousSpiMindreaderRtlTest(unittest.TestCase):
    def test_observe_learn_promote_and_impersonate_without_model_bytes(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        discovery = make_spi_case(1, True, request=0xA0, response=0x60)
        training = tuple(
            make_spi_case(1, True, request=value, response=lossy_response(value))
            for value in TRAINING_REQUESTS
        )
        held_out = make_spi_case(1, True, request=0xA7, response=0x63)

        lines: list[str] = [
            "pin_in = 4'h8; discover_enable = 1; passive_tick();",
            *(f"pin_in = 4'h{sample:x}; passive_tick();" for sample in discovery.waveform.samples[1:]),
            "discover_enable = 0; passive_tick();",
            'if (!physical_complete) fail("physical inference did not complete");',
            "learn_enable = 1;",
        ]
        for case in training:
            lines.extend(
                f"pin_in = 4'h{sample:x}; passive_tick();"
                for sample in case.waveform.samples
            )
            lines.append("passive_tick();")
        lines.extend(
            [
                "repeat (3) passive_tick();",
                'if (!direction_resolved || evidence_count != 8) fail("behavior did not resolve direction");',
                "learn_enable = 0; promote = 1; passive_tick(); promote = 0;",
                'if (!promotion_rejected || frozen_model_valid) fail("unauthorized promotion succeeded");',
                "ownership_granted = 1; timing_safe = 0; promote = 1; passive_tick(); promote = 0;",
                'if (!promotion_rejected || frozen_model_valid) fail("timing-unsafe promotion succeeded");',
                "timing_safe = 1; promote = 1; passive_tick(); promote = 0;",
                'if (!frozen_model_valid) fail("authorized promotion failed");',
                "passive_tick(); activate = 1; tick(); tick();",
                'if (!drive_enable || supervisor_state != 3) fail("admitted model did not activate");',
            ]
        )

        previous = held_out.waveform.samples[0]
        sampled = 0
        lines.append(f"pin_in = 4'h{previous & ~(1 << 2):x}; tick();")
        for sample in held_out.waveform.samples[1:]:
            wire_sample = sample & ~(1 << 2)
            previous_clock = previous & 1
            clock = sample & 1
            selected = not ((sample >> 3) & 1)
            sampling = selected and previous_clock == 1 and clock == 0
            lines.append(f"pin_in = 4'h{wire_sample:x}; #1;")
            if sampling:
                expected_bit = (0x63 >> (7 - sampled)) & 1
                lines.append(
                    f'if (pin_oe != 4\'b0100 || pin_out[2] != {expected_bit}) '
                    f'fail("held-out response bit {sampled}");'
                )
                sampled += 1
            lines.append("tick();")
            if sampling and sampled == 8:
                lines.append(
                    'if (!transfer_valid || transfer_request != 8\'hA7 || transfer_unknown) '
                    'fail("held-out transfer completion");'
                )
            if not selected:
                lines.append('if (pin_oe != 0) fail("deselect did not release response");')
            previous = sample
        self.assertEqual(sampled, 8)

        testbench = """
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,discover_enable=0,learn_enable=0,promote=0,timing_safe=1;
reg ownership_granted=0,activate=0,revoke=0,contradiction=0,contention=0,clear_fault=0;
reg [3:0] pin_in=4'h8;
wire [3:0] pin_out,pin_oe; wire physical_complete,direction_resolved;
wire frozen_model_valid,drive_enable; wire [7:0] evidence_count;
wire [2:0] supervisor_state,fault_reason; wire promotion_rejected;
wire transfer_valid; wire [7:0] transfer_request; wire transfer_unknown;
wire [1:0] inferred_select_pin,inferred_clock_pin,inferred_data_a_pin,inferred_data_b_pin;
wire inferred_select_active_level,inferred_clock_idle_level,inferred_sample_trailing;
always #5 clk=~clk;
autonomous_spi_mindreader dut(.*);
task tick; begin @(posedge clk); #1; end endtask
task passive_tick; begin tick(); if(pin_oe!=0) fail("learning drove a pin"); end endtask
task fail; input [8*120-1:0] m; begin $display("FAIL: %0s",m); $finish(1); end endtask
initial begin
repeat(2) tick(); rst_n=1;
""" + "\n".join(lines) + """
$display("AUTONOMOUS SPI MINDREADER PASS"); $finish(0);
end
endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "autonomous.vvp"
            sources = [
                "template_learner.v",
                "mindreader_supervisor.v",
                "spi_physical_learner.v",
                "spi_transaction_decoder.v",
                "dual_direction_learner.v",
                "learned_model_promoter.v",
                "template_spi_peripheral.v",
                "autonomous_spi_mindreader.v",
            ]
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 *(str(root / "src" / source) for source in sources), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(simulation.returncode, 0, simulation.stdout + simulation.stderr)
            self.assertIn("AUTONOMOUS SPI MINDREADER PASS", simulation.stdout)
