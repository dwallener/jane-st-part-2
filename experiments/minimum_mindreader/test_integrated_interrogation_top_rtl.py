import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class IntegratedInterrogationTopRtlTest(unittest.TestCase):
    def test_raw_passive_to_active_path_at_tinytapeout_boundary(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]
        sources = [
            "mindreader_core.v",
            "passive_bus_profiler.v",
            "serial_hypothesis_router.v",
            "uart_symbol_hypothesis_seq.v",
            "i2c_symbol_hypothesis.v",
            "generic_event_framer.v",
            "protocol_equivalence_classifier.v",
            "protocol_knowledge_reporter.v",
            "open_drain_bit_learner.v",
            "open_drain_address_probe.v",
            "adaptive_open_drain_interrogator.v",
            "template_learner.v",
            "mindreader_supervisor.v",
            "spi_physical_learner.v",
            "spi_transaction_decoder.v",
            "dual_direction_learner.v",
            "learned_model_promoter.v",
            "template_spi_peripheral.v",
            "spi_timing_guard.v",
            "pin_contention_monitor.v",
            "autonomous_spi_mindreader.v",
            "project.v",
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "integrated.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "integrated_interrogation_top_tb",
                    "-o",
                    str(output),
                    *(str(root / "src" / source) for source in sources),
                    str(root / "test" / "interrogation" / "models" /
                        "open_drain_bit_target_model.sv"),
                    str(root / "test" / "interrogation" /
                        "integrated_interrogation_top_tb.sv"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
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
            self.assertIn("INTEGRATED INTERROGATION TOP PASS", simulation.stdout)
