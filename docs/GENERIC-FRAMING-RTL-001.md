# GENERIC-FRAMING-RTL-001: Protocol-Neutral Event Boundaries

**Status:** integrated and tested  
**Date:** 2026-10-01

## Claim

The TinyTapeout-facing machine can accumulate framing evidence without first
assigning a protocol family or decoding bytes. The online event framer retains
three nonexclusive explanations:

1. **control enclosure** — one pin supplies both the first and last event and
   transitions exactly twice around other activity;
2. **quiet-gap separation** — transition bursts are separated by a bounded
   interval with no events; and
3. **repeated event count** — quiet-gap-separated bursts contain the same
   number of pin transitions.

These are structural observations, not claims that a pin is chip select, that
a gap is an official inter-frame interval, or that equal event counts imply a
fixed packet length. More than one candidate may survive.

## Online behavior

Every input sample updates per-pin transition counts, event age, current burst
size, and the repeated-size hypothesis. No trace replay or named decoder is
required. A pin becomes a control-enclosure candidate only when it occurs in
both the first and last event masks, has exactly two transitions, and encloses
additional activity.

The first RTL test demonstrates control enclosure, equal separated bursts that
retain both gap and fixed-count interpretations, and unequal bursts that remove
only the fixed-count interpretation. The TinyTapeout top-level test exposes
the same retained ambiguity through passive status pages and continuously
requires output enable to remain zero.

## Boundary

This block operates on raw transition events. It does not yet learn byte-valued
delimiter or length-field rules; those require a family-neutral symbol event
bus from the integrated frontends. It also does not authorize model promotion
or electrical drive. Its purpose is to preserve useful frame hypotheses before
the machine knows what the protocol is called.
