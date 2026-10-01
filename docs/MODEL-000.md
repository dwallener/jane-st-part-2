# MODEL-000: Serialized Hierarchical Learned Artifact

**Status:** first physical-plus-behavioral artifact implemented  
**Date:** 2026-09-30  
**Decision gate:** represent what was learned, what remains equivalent, and why
it is trusted within a compact machine-readable object

## Canonicalization

`SPI-001` ends with two behaviorally equivalent candidates differing only in
bit order. Storing two complete programs would confuse representation symmetry
with behavioral uncertainty.

The first hierarchical artifact therefore:

- selects MSB-first as an arbitrary canonical internal representation;
- stores one physical descriptor and one behavioral program; and
- records a bit-reversal equivalence flag.

For an LSB-first physical fixture, the canonical decoder sees bit-reversed
numeric words, and the canonical response program produces the correspondingly
bit-reversed response. The emitted wire sequence is unchanged.

## Binary format

The first SPI artifact is 22 bytes:

| Component | Bytes |
| --- | ---: |
| Magic, version, protocol kind | 4 |
| Physical flags | 1 |
| Four packed two-bit pin roles | 1 |
| Word width | 1 |
| Evidence waveform count | 1 |
| Physical hypotheses per waveform | 2 |
| Equivalent survivor count | 1 |
| Program length | 1 |
| Guarded behavioral program | 10 |
| **Total** | **22** |

The physical flags encode select polarity, clock idle level, sampling edge,
and bit-reversal equivalence. The behavioral payload is the existing canonical
10-byte guarded transition.

## Measured collapse

The demonstrated model records:

```text
8 waveforms × 384 physical hypotheses = 3,072 physical evaluations
4 physical survivors per isolated waveform
2 joint behavioral survivors
1 stored canonical model + 1 equivalence flag
```

The final artifact occupies 176 bits. This is close to the provisional 186-bit
state cost of one live learner context, and tiny relative to a 1 KiB-class
model memory. Forty-six such 22-byte artifacts fit in 1 KiB before indexing,
runtime state, alignment, or trace storage.

## Validation

- Every SPI mode and fixture bit order serializes to exactly 22 bytes.
- Decode reproduces the complete typed model.
- Corrupt magic and truncated payloads are rejected.
- A canonical model built from an LSB-first corpus predicts the held-out
  response in canonical space, proving wire behavior survives normalization.
- A reversible corpus with unresolved direction is rejected rather than
  canonicalized incorrectly.

## Provenance boundary

The first format stores only compact counts: waveform count, hypotheses per
waveform, and equivalent survivors. It does not yet retain trace hashes,
individual transition evidence, confidence scores, timestamps, or the reasons
each candidate was eliminated.

Those omissions are acceptable for measuring representation size but not yet
for the project's full "explain what it knows" promise.

## Next bounded step

`PROVENANCE-000.md` defines a 56-byte optional sidecar that lets a host answer:

- which observations support each transition;
- which uncertainty is representational equivalence versus missing evidence;
- which active probe would reduce genuine uncertainty; and
- whether a loaded model was learned, hand-authored, or host-refined.

Supported conclusions cite compact evidence fingerprints; equivalence and
unresolved uncertainty have distinct statuses; and missing electrical
direction produces a typed drive-ownership observation request. The 22-byte
real-time core remains unchanged.

`RTL-MODEL-000.md` closes the next representation boundary: synthesizable RTL
loads this exact 22-byte object, validates it atomically, exposes its learned
physical descriptor, and executes the packed behavioral transition on a
held-out request. Pin-level SPI execution remains a separate causality problem
rather than being hidden inside the word-level model.
