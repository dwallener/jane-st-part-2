import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class ProtocolEquivalenceClassifierRtlTest(unittest.TestCase):
    def test_unique_equivalent_and_insufficient_reports(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]
        testbench = r"""
`timescale 1ns/1ps
module tb;
reg router_ready=0,selected_sync_valid=0,uart_ready=0,uart_valid=0;
reg shared_two_wire_ready=0,shared_two_wire_valid=0,generic_ready=0;
reg[2:0]structural_classes=0,generic_classes=0;
wire ready,unique_result,equivalent_result,insufficient_result;wire[5:0]interpretation_mask;
wire[3:0]interpretation_count;
protocol_equivalence_classifier dut(.*);
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
router_ready=1;uart_ready=1;shared_two_wire_ready=1;generic_ready=1;
structural_classes=3'b001;uart_valid=1;#1;
if(!ready||!unique_result||equivalent_result||insufficient_result||interpretation_mask!=6'b000001)fail("unique async");
structural_classes=3'b010;uart_valid=0;selected_sync_valid=1;
generic_classes=3'b001;#1;
if(unique_result||!equivalent_result||insufficient_result||interpretation_mask!=6'b001010||interpretation_count!=2)fail("equivalent");
structural_classes=0;selected_sync_valid=0;generic_classes=0;#1;
if(unique_result||equivalent_result||!insufficient_result||interpretation_mask!=0)fail("insufficient");
generic_ready=0;#1;
if(ready||unique_result||equivalent_result||insufficient_result)fail("not ready");
$display("PROTOCOL EQUIVALENCE CLASSIFIER PASS");$finish(0);
end endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "classifier.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "protocol_equivalence_classifier.v"),
                 str(tb)], check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("PROTOCOL EQUIVALENCE CLASSIFIER PASS", simulation.stdout)
