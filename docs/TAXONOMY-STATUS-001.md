# TAXONOMY-STATUS-001: Structural Serial Protocol Taxonomy

**Status:** taxonomy stable; family-neutral RTL routing started  
**Date:** 2026-10-01

## Classification principle

The machine does not need to output a protocol brand name. `SPI`, `UART`, and
`I2C` are benchmark labels. Hardware instead retains structural hypotheses that
can compile into executable behavior:

```text
pin edges -> symbols -> frames -> fields -> integrity -> guarded behavior
```

The familiar quiet, synchronization, metadata, payload, integrity, and
termination lifecycle remains an explanation and search vocabulary. It is not
a hard-wired six-state pipeline: roles may be absent, repeated, nested, or
represented by external wires.

## Implementation matrix

| Layer | Implemented evidence | TinyTapeout-facing integration |
| --- | --- | --- |
| Electrical | activity, idle baseline, transition counts, edge correlation, direction/open-drain constraints | eight-pin quiet monitor and unknown-subset SPI role inference |
| Timing | clock edge, period, UART bit time, setup/launch margin | SPI timing admission plus UART periods 2–16 clocks |
| Symbols | width, order, polarity, parity, stop compatibility | bounded eight-bit SPI plus passive UART width/parity/stop candidates |
| Frames | select, UART start/stop, I2C start/stop/repeated-start, length/delimiter hypotheses | selected SPI, online shared-two-wire start/byte/ACK/stop, and generic control/gap/event-count candidates |
| Fields | constants, masks, copied/inverted bits, counters | mask/template SPI response |
| Integrity | XOR, additive rules, bounded CRC-8 catalog | experimental learner only |
| Behavior | guards, delay, state, next state, unknown handling | one bounded learned SPI transition family |
| Active learning | distinguishing observation/probe selection | proposal kernel exists; no wire-facing interrogator |

## Current structural routes

The first family-neutral RTL router accumulates one shared eight-pin evidence
window and preserves three nonexclusive candidate classes:

1. **asynchronous single-wire** — an active line observed at both levels;
2. **selected synchronous** — clock-like activity, a select-like two-edge line,
   and at least four active pins; and
3. **shared two-wire clocked** — exactly two active pins, one clock-like.

These are routing hints, not protocol decisions. A selected synchronous trace
may still leave asynchronous explanations alive. A two-wire trace does not by
itself prove open-drain electrical behavior. Ambiguity is explicitly reported.

## Inference scheduling rule

The architecture uses silicon parallelism where evidence must be observed at
the same instant, and reuses logic where hypotheses can be checked between
events:

- structural scouts run concurrently so no edge is missed;
- surviving hypotheses are eliminated incrementally as each observation
  arrives;
- equivalent survivors remain explicit rather than being forced into a label;
- deeper arithmetic or framing checks may share a time-multiplexed evaluator;
  and
- spare area is preferentially spent on evidence history, provenance, and
  executable behavior rather than duplicated complete decoders.

This is the intended meaning of "figure it out as we go": the machine updates
its model while traffic is arriving. A bounded post-capture sweep remains a
valid implementation tool, but it is not the defining architecture.

## Benchmark position

- SPI: learned wire emulation, including an unknown four-pin subset of eight.
- UART: passive symbol decoding on an unknown one-of-eight pin, with idle
  polarity and framing equivalence retained in the integrated top.
- I2C: online directed clock/data elimination, byte/ACK decoding, and
  open-drain-required classification integrated passively.
- Generic framing: online two-edge control enclosure, quiet-gap separation,
  and equal event-count candidates integrated passively and nonexclusively.
- Invented corpus: width, framing, integrity, state, corruption, ambiguity, and
  noncausal negative controls.

The integrated equivalence classifier now merges UART-like asynchronous,
selected-synchronous, shared-two-wire, control-enclosed, gap-framed, and
fixed-event-count survivors without forcing a name. The next gate is held-out
and malformed top-level traces.
