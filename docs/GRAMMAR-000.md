# GRAMMAR-000: Bounded Protocol Programs

**Status:** first executable representation implemented  
**Date:** 2026-09-30  
**Decision gate:** one representation must execute both learned stateless and
stateful behavior without embedding protocol-specific code

## Claim

Structured protocols are not arbitrary waveforms. They are compositions of a
small set of recurring roles: quiet or busy line state, synchronization,
metadata, payload, integrity, and termination or acknowledgement. Those roles
are a useful search prior, but they are not a mandatory linear pipeline.

Any role may be absent, repeated, nested, or represented by external signals.
An SPI chip-select can supply framing without an in-band preamble. An ACK may
be another complete frame. A continuous stream may revisit synchronization
without returning to idle. Consequently, the phases belong in the learner's
explanation and hypothesis grammar; they must not become six hard-wired states.

## Layered grammar

The proposed model separates five levels:

```text
pin edges -> symbols -> frames -> fields -> guarded behavioral transitions
```

Each level should compile into the level below it. Learning can therefore be
bounded independently:

- physical hypotheses cover idle level, active edge, period, and direction;
- symbol hypotheses cover sampling, bit order, and width;
- frame hypotheses cover sync, delimiters, lengths, and repeated regions;
- field hypotheses cover constants, copied fields, counters, and integrity;
- behavioral hypotheses cover request guards, state, responses, and deadlines.

This is a finite search only because every dimension has an explicit bound.
The device does not claim to infer unrestricted software, encrypted semantics,
or arbitrary black-box behavior.

## First executable behavioral IR

Experiments 000–003 justify one record type now:

```text
guarded transition:
    current state
    request mask and value
    eight response-bit expressions
    response delay
    next state
```

Response expressions share the RTL learner's 18-entry vocabulary: constant
zero, constant one, or copy/invert one of eight request bits. Each expression
therefore fits in five bits.

The canonical transition record is ten bytes:

| Field | Bits |
| --- | ---: |
| Current and next state | 8 |
| Request mask | 8 |
| Request value | 8 |
| Eight response expressions | 40 |
| Exact delay | 16 |
| **Total** | **80** |

The stateless learned example compiles to one record, or 10 bytes. The learned
two-state toggle example compiles to four records, or 40 bytes. Both execute on
the same interpreter and preserve held-out generalization. This is an initial
upper bound, not a compression result; shared control transitions and response
templates can be factored later if measurements justify the added machinery.

## Safety and determinism

The program validator rejects overlapping request guards within a state. An
unknown request produces no response and does not mutate state. Incomplete or
ambiguous learned models cannot be compiled. The binary encoding round-trips
through an independent decoder before behavioral comparison.

These rules make ambiguity a construction-time error instead of a runtime
priority convention.

## What this does not settle

This behavioral IR is deliberately not the final hardware instruction set.
The pin-level engine still needs evidence for edge predicates, shifting,
turnaround, output-enable control, loops, integrity operations, and deadlines.
Its encoding must wait for the I/O topology and synthesis measurements.

The six lifecycle roles likewise remain semantic annotations until the trace
experiments demonstrate reliable phase evidence. Naming a byte "header" or
"CRC" does not make the classification learned.

## Physical convention result

`PHYSICAL-000.md` now compiles a markerless serial trace into two artifacts:

1. a pin-level framing program that recovers the request byte; and
2. the existing behavioral program that selects and schedules the response.

The bounded search varies sampling edge and bit order. It uniquely recovers the
sampling edge but correctly retains both bit orders as an observationally
equivalent pair. This establishes the first justified physical operation—sample
on an inferred edge—and the first representation-level symmetry that the model
store should canonicalize rather than explore.

The next extension should remove either supplied pin roles or the fixed symbol
width, while keeping the other fixed so candidate growth remains measurable.
