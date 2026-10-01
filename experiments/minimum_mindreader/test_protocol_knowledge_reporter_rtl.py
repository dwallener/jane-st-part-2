import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class ProtocolKnowledgeReporterRtlTest(unittest.TestCase):
    def test_diagnosis_recommendation_and_safety_codes(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]
        testbench = r"""
`timescale 1ns/1ps
module tb;
reg observation_active=0,report_ready=0,activity_seen=0,bus_quiet=0;
reg evidence_saturated=0,contradiction=0,roles_resolved=0;
reg timing_admissible=0,ownership_granted=0,model_ready=0;
reg[5:0]interpretation_mask=0;reg[3:0]interpretation_count=0;
reg[7:0]closure_mask=0;
wire[7:0]knowledge_state,reason_code,next_evidence_code,safety_status;
protocol_knowledge_reporter dut(.*);
task fail;input[8*100-1:0]m;begin $display("FAIL: %0s",m);$finish(1);end endtask
initial begin
#1;if(knowledge_state!=0||reason_code!=1||next_evidence_code!=1)fail("observing");
report_ready=1;bus_quiet=1;#1;
if(knowledge_state!=3||reason_code!=2||next_evidence_code!=1)fail("quiet");
bus_quiet=0;activity_seen=1;#1;
if(knowledge_state!=3||reason_code!=3||next_evidence_code!=2)fail("open boundary");
closure_mask=8'h10;interpretation_mask=6'h10;interpretation_count=2;#1;
if(knowledge_state!=2||reason_code!=4||next_evidence_code!=3)fail("ambiguous");
interpretation_count=1;#1;
if(knowledge_state!=1||reason_code!=0||next_evidence_code!=4)fail("conclusion needs electrical evidence");
roles_resolved=1;timing_admissible=1;model_ready=1;#1;
if(next_evidence_code!=5||safety_status[0])fail("authorization required");
ownership_granted=1;#1;
if(next_evidence_code!=0||!safety_status[0])fail("admitted");
evidence_saturated=1;#1;
if(knowledge_state!=6||reason_code!=6||next_evidence_code!=6||safety_status[0])fail("saturation precedence");
evidence_saturated=0;contradiction=1;#1;
if(knowledge_state!=5||reason_code!=7||next_evidence_code!=1||safety_status[0])fail("contradiction");
$display("PROTOCOL KNOWLEDGE REPORTER PASS");$finish(0);
end endmodule
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            tb = Path(temporary_directory) / "tb.v"
            tb.write_text(testbench)
            output = Path(temporary_directory) / "knowledge.vvp"
            compile_result = subprocess.run(
                [iverilog, "-g2012", "-s", "tb", "-o", str(output),
                 str(root / "src" / "protocol_knowledge_reporter.v"), str(tb)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            simulation = subprocess.run(
                [vvp, str(output)], check=False, capture_output=True, text=True
            )
            self.assertEqual(
                simulation.returncode, 0, simulation.stdout + simulation.stderr
            )
            self.assertIn("PROTOCOL KNOWLEDGE REPORTER PASS", simulation.stdout)
