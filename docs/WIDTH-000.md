# WIDTH-000: Frame Width Is Observable; Symbol Width May Not Be

**Status:** fixed-width phase inference implemented  
**Date:** 2026-09-30  
**Decision gate:** distinguish physical evidence from representational naming

## Question

Once pin roles and sampling edge are known, what does a markerless trace reveal
about width?

Two different quantities are easy to conflate:

1. **Framed phase width:** the number of sampled bits between observable phase
   boundaries such as select and response-valid.
2. **Symbol width:** whether those bits should be described as one word, two
   nibbles, four two-bit symbols, or individual bits.

## Experiment

The width observer counts stable sampling edges independently in request and
response phases. Every trace in the corpus must have the same phase shape.
The experiment uses both eight-bit and six-bit fixtures to prove that the
result is not hard-coded to a byte.

For each observed shape, it enumerates every common divisor as a compatible
symbol width, subject to an explicit maximum bound.

## Result

The eight-bit fixture produces:

```text
phase shape:             request=8 bits, response=8 bits
compatible symbol width: 1, 2, 4, or 8 bits
```

The six-bit fixture produces:

```text
phase shape:             request=6 bits, response=6 bits
compatible symbol width: 1, 2, 3, or 6 bits
```

The physical frame width is uniquely observed because select and valid expose
the boundaries. Symbol width is not uniquely observed: all divisor-based
segmentations describe the same edge sequence.

## Architectural consequence

The capture and execution engine needs bit counts, not human concepts such as
"byte." A learned program can retain the whole framed bit vector and attach
field boundaries only when additional evidence requires them—for example:

- a length field governs a repeated region;
- a delimiter recurs at a particular alignment;
- a checksum operates over fixed-width units;
- an active probe changes one candidate field independently; or
- the host supplies a convention.

This argues for bit-addressed capture plus optional field descriptors, rather
than baking 8-bit symbols into the protocol engine.

## Guardrails and non-claims

- Variable phase widths are explicitly rejected by this fixed-width model;
  they belong in the subsequent length/delimiter hypothesis.
- Select and response-valid still expose exact boundaries.
- Pin roles and sampling edge are inputs from the preceding bounded search.
- Widths above the configured search bound are not considered.
- The experiment does not infer semantic field boundaries.

## Next bounded question

The natural extension is variable-length framing. Hold physical roles fixed
and compare two finite hypotheses: an explicit length field versus a terminal
delimiter. That begins to exercise the metadata and payload phases without
assuming either one is mandatory.
