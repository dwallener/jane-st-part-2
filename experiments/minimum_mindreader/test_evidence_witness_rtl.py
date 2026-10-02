import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from known_protocol_corpus import DigitalWaveform, benchmark_cases
from waveform_adapter import (
    AnonymousEdgeEvent,
    AnonymousEdgeTrace,
    compress_waveform,
    expand_edge_trace,
)


class EvidenceWitnessRtlTest(unittest.TestCase):
    def test_rtl_witness_matches_independent_python_reference(self) -> None:
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        self.assertIsNotNone(iverilog)
        self.assertIsNotNone(vvp)
        assert iverilog is not None and vvp is not None
        root = Path(__file__).resolve().parents[2]

        witnesses = tuple(
            (case.name, DigitalWaveform(8, case.waveform.samples))
            for case in benchmark_cases()
        ) + (("quiet_8pin", DigitalWaveform(8, (0xA5,) * 9)),)

        for name, waveform in witnesses:
            with self.subTest(case=name):
                expected = compress_waveform(waveform)
                assignments = "\n".join(
                    f"    pin_sample = 8'h{sample:02x}; tick();"
                    for sample in waveform.samples[1:]
                )
                testbench = f"""`timescale 1ns / 1ps
`default_nettype none
module tb;
  reg clk = 0;
  reg rst_n = 0;
  reg capture_enable = 0;
  reg clear = 0;
  reg [7:0] pin_sample = 0;
  reg pop = 0;
  wire valid;
  wire [15:0] event_delta;
  wire [7:0] event_sample;
  wire [7:0] event_changed;
  wire [7:0] initial_sample;
  wire [15:0] trailing_delta;
  wire capture_complete;
  wire [7:0] event_count;
  wire overflow;
  wire evidence_valid;

  always #5 clk = ~clk;
  edge_trace_capture #(.PIN_WIDTH(8), .DEPTH(128), .DELTA_BITS(16)) dut (
    .clk(clk), .rst_n(rst_n), .capture_enable(capture_enable),
    .clear(clear), .pin_sample(pin_sample), .pop(pop), .valid(valid),
    .event_delta(event_delta), .event_sample(event_sample),
    .event_changed(event_changed), .initial_sample(initial_sample),
    .trailing_delta(trailing_delta), .capture_complete(capture_complete),
    .event_count(event_count), .overflow(overflow),
    .evidence_valid(evidence_valid)
  );

  task tick;
    begin @(posedge clk); #1; end
  endtask

  initial begin
    repeat (2) tick();
    rst_n = 1;
    pin_sample = 8'h{waveform.samples[0]:02x};
    capture_enable = 1;
    tick();
{assignments}
    capture_enable = 0;
    tick();
    $display("HEADER %02x %0d %0d %0d %0d", initial_sample,
             trailing_delta, capture_complete, overflow, event_count);
    pop = 1;
    while (valid) begin
      $display("EVENT %0d %02x %02x", event_delta, event_sample, event_changed);
      tick();
    end
    $finish(0);
  end
endmodule
`default_nettype wire
"""
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary = Path(temporary_directory)
                    tb = temporary / "evidence_witness_tb.v"
                    output = temporary / "evidence_witness.vvp"
                    tb.write_text(testbench)
                    compile_result = subprocess.run(
                        [
                            iverilog,
                            "-g2012",
                            "-s",
                            "tb",
                            "-o",
                            str(output),
                            str(root / "src" / "edge_trace_capture.v"),
                            str(tb),
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
                    simulation.returncode, 0, simulation.stdout + simulation.stderr
                )

                header = re.search(
                    r"^HEADER ([0-9a-f]+) (\d+) (\d+) (\d+) (\d+)$",
                    simulation.stdout,
                    re.MULTILINE,
                )
                self.assertIsNotNone(header, simulation.stdout)
                assert header is not None
                initial, trailing, complete, overflow, count = header.groups()
                events = tuple(
                    AnonymousEdgeEvent(int(delta), int(value, 16), int(changed, 16))
                    for delta, value, changed in re.findall(
                        r"^EVENT (\d+) ([0-9a-f]+) ([0-9a-f]+)$",
                        simulation.stdout,
                        re.MULTILINE,
                    )
                )
                actual = AnonymousEdgeTrace(
                    pin_count=8,
                    initial_value=int(initial, 16),
                    events=events,
                    trailing_cycles=int(trailing),
                )

                self.assertEqual(int(complete), 1)
                self.assertEqual(int(overflow), 0)
                self.assertEqual(int(count), len(events))
                self.assertEqual(actual, expected)
                self.assertEqual(expand_edge_trace(actual), waveform)


if __name__ == "__main__":
    unittest.main()
