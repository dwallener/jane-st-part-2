# FRAMING-000: Length Fields Versus Delimiters

**Status:** first variable-length framing competition implemented  
**Date:** 2026-09-30  
**Decision gate:** predict unseen boundaries rather than merely redescribe
already framed training examples

## Claim

After physical sampling and symbol extraction, a bounded learner can distinguish
two common variable-length framing programs:

```text
length field: total frame bytes = frame[field_index] + bias
delimiter:    frame ends at an unescaped terminal byte
```

The training corpus contains framed examples. The test corpus is a concatenated
symbol stream with no boundaries. A hypothesis passes only if it segments that
held-out stream correctly.

## Bounded search

Length hypotheses enumerate:

- a field position from zero through a configured maximum;
- a signed additive bias from a configured finite range; and
- a maximum frame length.

The delimiter hypothesis uses a terminal byte shared by every training frame.
It is admitted only when that byte never occurs inside a frame. Escaping and
byte stuffing are deliberately out of scope for this experiment.

## Results

Three controls are included:

1. A length-prefixed corpus uniquely learns `total = frame[0] + 1` and segments
   a held-out stream containing frames of new lengths.
2. A delimiter corpus uniquely learns terminal `0x7E` and segments a held-out
   stream containing unseen payloads.
3. A deliberately ambiguous corpus fits both explanations. The learner retains
   both until one additional frame eliminates either length or delimiter.

Truncated held-out streams are rejected. An interior unescaped delimiter is not
silently treated as valid evidence for delimiter framing.

## Why this matters

This is the first experiment to assign competing structural roles to observed
symbols. One candidate interprets a byte as header metadata controlling the
payload extent; the other interprets a byte as trailer termination. Neither
role is hard-wired into the phase sequence.

The executable result is still small:

```text
LENGTH(field_index, bias, maximum)
DELIMITER(value, maximum)
```

These are plausible protocol-program operations, but their final encoding and
hardware implementation remain deferred until synthesis establishes cost.

## Non-claims

- Symbols are already decoded and byte-sized.
- Training frame boundaries are supplied.
- Length scaling, multi-byte lengths, escaping, COBS, and checksums are absent.
- Variable request/response behavior is not learned in the same experiment.
- Corrupted frames and noisy links are not modeled.

## Next bounded question

`INTEGRITY-000.md` implements the next phase with constant, XOR, additive,
two's-complement additive, and a four-member CRC-8 catalog. Candidate rules
validate held-out frames and retain ambiguity when several explanations fit.
