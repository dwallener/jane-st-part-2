# I2C-RTL-001: Online Shared-Two-Wire Elimination

**Status:** integrated and tested  
**Date:** 2026-10-01

## Claim

The TinyTapeout-facing machine passively considers every directed clock/data
assignment across the eight anonymous pins. Each new sample updates those
hypotheses in place. Candidates must begin in the released-high state and then
exhibit a coherent sequence of:

1. data falling while clock is high (start);
2. data sampled on clock rising edges;
3. eight data bits followed by one ACK/NACK bit;
4. one or more complete byte/ACK groups; and
5. data rising while clock is high (stop).

The implementation retains role ambiguity when multiple directed assignments
remain. For a unique candidate it also retains the first two decoded bytes,
their ACK bits, and the decoded byte count. Any surviving interpretation is
marked `open_drain_required`; that is an execution constraint, not permission
to drive.

## Why this is the intended architecture

Unlike the first UART implementation, this learner does not capture a trace
and decode it afterward. Sixty-four bounded directed assignments carry small
state records and are pruned as the traffic happens. This is the first literal
"figure it out as we go" engine in the wire-facing RTL.

The parallel first implementation costs 8,555 generic synthesized cells. That
is acceptable for establishing semantics and measuring the backend, but the
state records are deliberately exposed as an optimization target: inactive
roles can later share byte storage without changing the inference contract.

## Refusal and safety boundary

The block has no output-data or output-enable port. A missing start, incomplete
byte-only trace, missing stop, or contradictory role assignment cannot produce
a valid candidate. The TinyTapeout integration exposes only candidate count and
clock/data masks; it does not connect this evidence to model promotion or the
existing SPI execution path.

The focused RTL test remaps the canonical acknowledged write onto clock pin 2
and data pin 5, recovers bytes `A0 2A` with ACK bits `0,0`, and rejects the same
trace without STOP. The top-level cocotb test independently confirms the role
masks, verifies that SPI inference does not complete, and requires every output
enable to remain low.
