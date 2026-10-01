# PHYSICAL-000: Bounded Framing Hypotheses

**Status:** sampling, ordering, and pin-role searches implemented  
**Date:** 2026-09-30  
**Decision gate:** recover an executable transaction corpus from markerless
edges without silently resolving unobservable conventions

## Scope

This experiment keeps five facts fixed: clock, request-data, select,
response-data, and response-valid pin roles, plus an eight-bit symbol width.
It removes two previously supplied conventions:

- whether data is sampled on the rising or falling clock edge; and
- whether temporal bits are interpreted most- or least-significant first.

The search enumerates all four hypotheses. Each candidate must decode every
trace, satisfy a digital setup constraint, and produce a complete behavioral
model across the corpus.

## Fixture

The configurable serial fixture changes data on the edge opposite its sampling
edge. A candidate that samples an event where its data line also changes is
rejected because the trace provides no ordering or setup guarantee at that
instant.

The test runs both a rising-edge/MSB-first fixture and a falling-edge/LSB-first
fixture. All markers are absent.

## Result

The search uniquely recovers the sampling edge in both fixtures. It does not
uniquely recover bit order: both bit-order interpretations produce complete,
internally consistent behavioral models.

This is not a learner failure. Reversing every request bit, response bit, mask,
and template yields an observationally equivalent description. With no
external numeric convention, "bit zero" is only a name. The emulator can use
either representation as long as decoding and encoding agree.

The correct inference result is therefore an equivalence class:

```text
sample edge = rising
bit order   = {MSB-first, LSB-first} modulo consistent bit reversal
```

or the corresponding class for falling-edge capture. The implementation keeps
both candidates rather than awarding false confidence to an arbitrary order.

## Architectural consequence

Sampling edge is a physical hypothesis with observable setup evidence. Bit
order is representational until some asymmetric external fact breaks the
symmetry—for example, a known sync word, arithmetic length relationship, CRC
convention, or host annotation.

The pin-level learner should therefore canonicalize equivalent models or carry
a compact transform tag. It should not spend memory and active probes trying to
distinguish names that generate identical pin behavior.

## Remaining non-claims

- Pin directions and the number of relevant pins are still supplied.
- Symbol width is still supplied.
- The clock is externally visible and regular.
- There is exactly one request and one response byte per transaction.
- Select and response-valid expose the phase boundaries.
- No jitter, metastability, glitches, or oversampling are modeled.

## Pin-role extension

The second search keeps direction and eight-bit width fixed, but removes the
role labels from three controller-to-device pins and two device-to-controller
pins. It enumerates:

```text
3! input assignments × 2! output assignments × 2 edges × 2 bit orders
= 48 hypotheses
```

For both the default wiring and a fully permuted fixture, the corpus uniquely
identifies clock, request-data, select, response-data, response-valid, and the
sampling edge. The two equivalent bit orders remain, leaving two survivors
from 48 hypotheses. A physical hypothesis is admitted only when the decoded
corpus produces both a complete response model and a variable request family.
This rejects the misleading all-constant "model" that one isolated exchange
can always produce.

This is the first end-to-end evidence that behavioral regularity can disambiguate
physical structure: candidate pin maps are not selected from activity counts
alone; they must decode the entire corpus into a complete learned model.

## Next bounded question

Symbol width remains supplied. Removing it next should distinguish the directly
observable number of bits in a selected phase from the generally unobservable
choice to name those bits as one word, two nibbles, or eight one-bit symbols.
