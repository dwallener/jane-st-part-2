import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class HierarchicalModelExecutorRtlTest(unittest.TestCase):
    def test_python_artifact_loads_and_executes_in_rtl(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog, "iverilog is required for the RTL model test")
        self.assertIsNotNone(vvp, "vvp is required for the RTL model test")
        assert iverilog is not None
        assert vvp is not None

        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "hierarchical_model_executor.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "tb_hierarchical_model_executor",
                    "-o",
                    str(output),
                    str(root / "src" / "hierarchical_model_executor.v"),
                    str(root / "test" / "hierarchical_model_executor_tb.v"),
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
            self.assertIn("HIERARCHICAL MODEL EXECUTOR PASS", simulation.stdout)
