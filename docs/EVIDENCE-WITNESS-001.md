# EVIDENCE-WITNESS-001: Independently Replayable Capture

**Status:** implemented standalone; top-level integration not yet admitted
**Date:** 2026-10-02

## Question

Can the synthesizable recorder produce enough evidence for an independent
implementation to reconstruct exactly what it sampled, including the quiet
time at both ends?

This is narrower than protocol inference and stronger than checking that a
decoder returned the expected brand or byte. It tests the evidence substrate
without using any protocol decoder.

## Witness format

One completed observation contains:

| Field | Meaning |
| --- | --- |
| `initial_sample` | Complete anonymous pin value at capture admission. |
| `event_delta` | Sample clocks since the preceding baseline or event. |
| `event_sample` | Complete anonymous pin value after the event. |
| `event_changed` | XOR of the preceding value and `event_sample`. |
| `trailing_delta` | Unchanged sampled intervals after the final event. |
| `capture_complete` | The observation window was explicitly closed. |
| `overflow` | At least one event or time interval was not representable. |

`evidence_valid` remains false after overflow. Completion and validity are
separate: a closed observation may be known to be lossy.

## Independent check paths

The two paths share only the sampled waveform:

1. `src/edge_trace_capture.v` observes one sample per clock and emits FIFO
   records plus observation closure.
2. `waveform_adapter.compress_waveform` derives an `AnonymousEdgeTrace` in
   Python from the original sample sequence.

`test_evidence_witness_rtl.py` feeds every canonical SPI, UART, and I2C corpus
waveform to the RTL, parses only its published witness, compares every field to
the Python result, and expands the RTL-derived witness back into the original
waveform. All 13 protocol cases plus a quiet eight-pin negative control pass. A
matching protocol decode is not sufficient to pass.

## Negative evidence

The existing supervisor/capture test fills the bounded FIFO past capacity and
requires `overflow=1` and `evidence_valid=0`. Truncation therefore cannot be
silently promoted into a valid observation.

## Discovered defect and correction

The original recorder stored event deltas, samples, and changed masks, but did
not expose its baseline or the time between the final edge and observation
closure. That stream was not independently replayable. The correction adds
`initial_sample`, `trailing_delta`, and `capture_complete` without integrating
the recorder into the tapeout top.

## Admission boundary

Passing this experiment earns the statement “the bounded recorder has an
independently checked lossless format when `capture_complete=1` and
`evidence_valid=1`.” It does not prove that:

- capture began before the real transaction;
- the sampling clock observed transitions faster than itself;
- any inferred packet boundary is universally correct; or
- the current top has budgeted and integrated this recorder.
