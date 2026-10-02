# TRACE-000: Cycle-Delta Edge Trace

**Status:** software format implemented; anonymous RTL witness independently checked
**Date:** 2026-10-02

## Purpose

The trace is the common evidence format between capture hardware, software
experiments, RTL simulation, and eventual FPGA tests. It records pin changes
without embedding UART, SPI, I2C, or synthetic-link packets in the storage
format.

Experiment 001 uses supplied markers to preserve known transaction boundaries.
Experiment 002 will attempt to infer those boundaries. A marker is therefore
training metadata, not a pin and not evidence that framing has been learned.

## Record

Each event contains:

| Field | Meaning |
| --- | --- |
| `delta_cycles` | Cycles since the preceding event. |
| `input_value` | Complete sampled input-pin value after this event. |
| `input_changed` | Bit mask of input pins changed by this event. |
| `output_value` | Complete sampled peripheral-output value after this event. |
| `output_changed` | Bit mask of output pins changed by this event. |
| `marker` | Optional supplied boundary annotation. |

Values and changed masks are eight bits in Experiment 001. The format can be
widened later without changing its semantics.

## Canonical rules

- The implicit pin state before the first event is all zero.
- `delta_cycles` is non-negative. Zero is permitted for a marker attached to
  the same cycle as the previous edge.
- Each changed mask must exactly equal the XOR of the previous and new value.
- Events with no pin change are permitted only when they carry a marker.
- Pin values are authoritative; changed masks are integrity checks and permit
  efficient hardware filtering.
- Events are ordered. Two zero-delta events must not be reordered.

Experiment 001 defines these markers:

- `request_start`
- `request_end`
- `response_start`
- `response_end`

## CSV representation

The interchange form has this header:

```text
delta_cycles,input_value,input_changed,output_value,output_changed,marker
```

Pin fields are written as two-digit hexadecimal values. An absent marker is an
empty field. The Python implementation validates the canonical rules when a
trace is constructed or parsed.

## Experiment 001 synthetic link

The format itself has no pin meanings. The Experiment 001 fixture assigns:

| Direction | Bit | Meaning |
| --- | ---: | --- |
| controller to peripheral | 0 | clock |
| controller to peripheral | 1 | request data |
| controller to peripheral | 2 | select, active high |
| peripheral to controller | 0 | response data |
| peripheral to controller | 1 | response valid, active high |

Bytes are shifted most-significant bit first and sampled on rising clock edges.
The response-valid rising edge makes the response start physically observable.
The interval between request completion and that edge is the response delay.
These rules belong to the synthetic fixture's codec, not to the generic trace
container or the learner.

The markerless Experiment 001 path strips all annotations before decoding. It
uses select edges to delimit the transaction, response-valid to distinguish
request and response phases, and clock edges to sample data. It does not yet
infer pin roles, active levels, sampling edge, byte width, or bit order.

## Synthesizable anonymous witness

`src/edge_trace_capture.v` now implements the input-side hardware subset. A
closed witness publishes the initial pin sample, delta-timed complete samples
and changed masks, the quiet tail after the final event, completion, and
overflow. `docs/EVIDENCE-WITNESS-001.md` defines the independent RTL/Python
comparison.

The hardware witness has no supplied markers and no separate output channel;
all observed pins are anonymous. The richer Experiment 001 CSV remains a host
interchange format rather than the literal FIFO layout.

## Hardware implications still deferred

The standalone recorder chooses parameterized counter width, FIFO depth, and
explicit overflow behavior for testing. Top-level allocation, marker encoding,
capture bandwidth, and whether records are retained or streamed remain
architecture decisions. The witness is not yet part of the tapeout top.
