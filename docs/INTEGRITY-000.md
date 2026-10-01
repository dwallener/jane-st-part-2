# INTEGRITY-000: Bounded Trailer Inference

**Status:** one-byte integrity competition implemented  
**Date:** 2026-09-30  
**Decision gate:** validate unseen frames and preserve ambiguity across compact
integrity rules

## Hypothesis catalog

The first integrity learner assumes the final byte of each framed sequence is a
trailer. It compares eight fixed hypotheses:

- a constant trailer, used as the negative control;
- bytewise XOR;
- additive sum modulo 256;
- two's-complement additive sum; and
- CRC-8/SMBUS, CRC-8/SAE-J1850, CRC-8/MAXIM-DOW, and CRC-8/ROHC.

The CRC catalog is deliberately named and finite. The learner does not search
all polynomials, initial values, reflection choices, or output transforms.

## Results

Independent generated corpora uniquely recover XOR, sum, negative sum, and
each catalog CRC. The standard `123456789` check vector verifies all four CRC
implementations against their published check values before they are used as
learning candidates.

A learned CRC validates an unseen frame and rejects a one-bit payload
corruption without changing its trailer.

## Ambiguity and probing

Two training frames are constructed so their XOR is always `0x30`. Both a
constant `0x30` trailer and XOR therefore fit. The learner retains every
matching rule and proposes a one-byte payload whose predicted trailers differ.
One additional XOR-protected frame eliminates the constant explanation.

This is the same active-learning pattern used for response templates, now
applied to structural integrity rather than request/response behavior.

## Hardware relevance

Every dynamic rule here has an eight-bit streaming state:

```text
XOR:          state <- state XOR byte
SUM:          state <- state + byte
NEGATIVE SUM: state <- -(state + byte) at trailer
CRC-8:        eight-bit LFSR update per input bit or byte
```

The storage cost is trivial; combinational update cost and throughput determine
whether several rules should run in parallel during learning or be evaluated
serially. Constant, XOR, and sum are nearly free compared with a general
processor. CRC earns hardware only if synthesis confirms that a configurable
LFSR is cheaper than catalog-specific alternatives or host assistance.

## Non-claims

- The trailer is exactly one byte and its position is supplied by framing.
- Only the listed CRC catalog is searched.
- Coverage ranges, residue conventions, and multi-byte trailers are absent.
- Escaping and corruption during training are absent.
- Passing a checksum does not prove that the field is semantically integrity.

## Next bounded question

The model pieces now cover physical roles, sampling, fixed and variable
framing, field transformations, state, timing, and integrity in isolation. The
next experiment should compose them into one hierarchical protocol description
and measure candidate growth, memory, and execution cost before adding another
hypothesis family.
