# HARDWARE-000: First Evidence-Backed RTL Primitive

**Status:** first kernel implemented  
**Date:** 2026-09-30

## Evidence from Experiments 000–003

The software experiments now require five operations that plausibly belong in
hardware:

1. capture pin edges with cycle deltas;
2. update a stable request mask and value from repeated observations;
3. retain every response-bit expression consistent with the evidence;
4. retain exact response timing until contradictory evidence appears; and
5. execute a resolved mask/template model with deterministic timing.

The experiments do not yet justify a processor, instruction set, arbitrary
state-machine learner, CRC unit, or a specific trace-memory organization.

## Compact response uncertainty

For an 8-bit request, the Experiment 000 response language has 18 possible
expressions per response bit:

| Candidate index | Expression |
| ---: | --- |
| 0 | constant zero |
| 1 | constant one |
| `2 + 2*i` | copy request bit `i` |
| `3 + 2*i` | invert request bit `i` |

An 8-bit response therefore needs eight 18-bit candidate masks: 144 bits. A
new observation evaluates all 18 expressions and intersects each mask with the
matching expressions. This represents the 256 complete models in Experiment
003 without storing 256 models.

Copy and invert candidates sourced from request bits that never varied are
suppressed from the effective masks. This matches the software learner's rule
that stable request bits define the request-family predicate rather than
response fields.

## First RTL boundary

`template_learner` consumes one already-framed observation at a time:

```text
observe(request, response, delay_cycles)
```

It produces:

- stable request mask and value;
- eight packed response candidate masks;
- exact delay plus a validity flag;
- evidence count; and
- a `model_complete` flag when every response bit has one effective candidate.

The module deliberately does not capture pins, discover framing, or choose
probes. It isolates the streaming update that is both supported by the
experiments and cheap enough to imagine duplicating for bounded contexts.

`template_executor` is the paired replay kernel. It accepts a request only
when idle, checks the learned predicate, evaluates the sole surviving
expression for each response bit, and pulses the response exactly the learned
number of clocks later. Out-of-family requests and unresolved models produce
an explicit `unknown` pulse rather than a guessed response. The first pipeline
test trains the RTL directly and then executes the held-out `0xA7 -> 0x67`
exchange after six clocks.

## Provisional storage cost

One context currently requires approximately:

| State | Bits |
| --- | ---: |
| Request mask and value | 16 |
| Raw response candidates | 144 |
| Delay and validity | 17 |
| Evidence count and flags | 9 |
| **Total** | **186** |

Two contexts are about 372 bits before transition metadata. Trace storage is
likely much larger: the present uncompressed record is 48 bits per edge event.
That makes memory format and event reduction higher-risk questions than the
template update datapath.

## Explicitly deferred problems

- Compact on-chip state discovery. Experiment 002 currently evaluates a full
  learner per possible control request in software.
- Optimal probe scoring. Experiment 003 enumerates complete models; hardware
  should operate on factored candidate masks or accept host assistance.
- Candidate overflow and aging policies.
- Approximate or ranged timing models.
- Trace buffer width, depth, overflow, and compression.
- Pin-role and framing discovery.

These are not implementation omissions disguised as future polish. They are
open architecture decisions whose costs must be measured before integration.

## RTL gate

The first kernel passes when RTL simulation proves that:

- sparse `0xA0`/`0xAF` evidence remains ambiguous;
- observations `0xA3` and `0xA5` reduce every response bit to the intended
  expression;
- the learned request predicate is `mask=0xF0, value=0xA0`;
- a conflicting delay clears timing validity and model completeness; and
- reset clears all learned state.

The paired executor passes when RTL simulation additionally proves that:

- the held-out `0xA7` request is accepted by the learned predicate;
- its response is constructed as `0x67` without a replay-table entry;
- `response_valid` arrives exactly six clocks after request acceptance;
- the executor applies backpressure while the response is pending; and
- the out-of-family `0xB7` request produces `unknown` and no response.
