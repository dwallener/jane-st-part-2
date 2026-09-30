import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TemplateLearnerRtlTest(unittest.TestCase):
    def test_streaming_candidate_masks(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog, "iverilog is required for the RTL kernel test")
        self.assertIsNotNone(vvp, "vvp is required for the RTL kernel test")
        assert iverilog is not None
        assert vvp is not None

        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "template_learner.vvp"
            compile_result = subprocess.run(
                [
                    iverilog,
                    "-g2012",
                    "-s",
                    "tb_template_learner",
                    "-o",
                    str(output),
                    str(root / "src" / "template_learner.v"),
                    str(root / "test" / "template_learner_tb.v"),
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
            self.assertIn("TEMPLATE LEARNER PASS", simulation.stdout)

