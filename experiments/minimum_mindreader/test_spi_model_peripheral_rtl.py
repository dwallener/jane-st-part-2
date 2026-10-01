import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SpiModelPeripheralRtlTest(unittest.TestCase):
    def test_serialized_model_executes_on_anonymous_spi_pins(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog, "iverilog is required for the SPI RTL test")
        self.assertIsNotNone(vvp, "vvp is required for the SPI RTL test")
        assert iverilog is not None
        assert vvp is not None
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "spi_model_peripheral.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "tb_spi_model_peripheral",
                    "-o",
                    str(output),
                    str(root / "src" / "hierarchical_model_executor.v"),
                    str(root / "src" / "spi_model_peripheral.v"),
                    str(root / "test" / "spi_model_peripheral_tb.v"),
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
            self.assertIn("SPI MODEL PERIPHERAL PASS", simulation.stdout)
