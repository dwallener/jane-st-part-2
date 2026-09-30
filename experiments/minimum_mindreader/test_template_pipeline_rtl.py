import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TemplatePipelineRtlTest(unittest.TestCase):
    def test_learn_and_execute_held_out_request(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog, "iverilog is required for the RTL pipeline test")
        self.assertIsNotNone(vvp, "vvp is required for the RTL pipeline test")
        assert iverilog is not None
        assert vvp is not None

        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "template_pipeline.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "tb_template_pipeline",
                    "-o",
                    str(output),
                    str(root / "src" / "template_learner.v"),
                    str(root / "src" / "template_executor.v"),
                    str(root / "test" / "template_pipeline_tb.v"),
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
            self.assertEqual(simulation.returncode, 0, simulation.stdout + simulation.stderr)
            self.assertIn("TEMPLATE PIPELINE PASS", simulation.stdout)
