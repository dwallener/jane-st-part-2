import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SupervisorCaptureRtlTest(unittest.TestCase):
    def test_passive_supervisor_and_loss_detecting_capture(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "supervisor_capture.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb_supervisor_capture", "-o", str(output),
                 str(root / "src" / "mindreader_supervisor.v"),
                 str(root / "src" / "edge_trace_capture.v"),
                 str(root / "test" / "supervisor_capture_tb.v")],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(simulation.returncode, 0, simulation.stdout + simulation.stderr)
            self.assertIn("SUPERVISOR CAPTURE PASS", simulation.stdout)
