# RTL-MODEL-000: Execute the Learned Artifact Directly

**Status:** first serialized-model RTL boundary implemented  
**Date:** 2026-09-30  
**Decision gate:** prove that the software-produced model is hardware input,
not merely a report format

## Result

`hierarchical_model_executor.v` consumes the exact 22-byte artifact defined in
`MODEL-000.md`. A host writes the bytes into a model slot and pulses commit.
The loader atomically validates the header, physical descriptor, stateless
transition shape, guard, and every response-expression opcode before exposing
the model to the executor.

The RTL then:

- exposes the learned select, clock, request, and response pin roles;
- exposes select polarity, clock idle level, sampling edge, and bit-order
  equivalence;
- evaluates the packed 10-byte guarded transition directly;
- produces the learned response and delay for an accepted request; and
- explicitly refuses requests outside the learned family.

The regression loads an artifact emitted by the Python hierarchy for SPI mode
0, evaluates the held-out request `0xA7`, and obtains `0x63`. It also rejects an
out-of-family request and revokes the model when its magic is corrupted.

## Deliberate first-format limit

The 22-byte format contains one stateless transition. The loader therefore
admits only a 10-byte program with state `0 -> 0` and an eight-bit word. This is
a versioned limitation: multi-transition stateful programs require a larger
slot and an indexed transition search.

## Causality boundary before pin-level SPI

This executor operates at the decoded-word boundary. A fully generic SPI slave
cannot always emit a response in the same transfer after learning only a
transaction-level function: response bit zero may depend on request bit seven,
which has not arrived yet. The next pin-level step must therefore make timing
causality explicit. It can admit stream-causal models, learn a
request-then-response transaction shape, or deliberately use one-frame
latency. Silently assuming any of these would overclaim what the artifact
proves.

That constraint is useful: the mindreader has found a new hypothesis axis—not
merely *what* function relates request and response, but *when* each output bit
becomes computable.

`CAUSALITY-000.md` implements that axis. The present learned SPI relation is
same-symbol causal in all eight fixtures: it needs a measured launch-to-sample
budget, but never depends on a future request bit.

`SPI-RTL-000.md` crosses the pin boundary for the first time. The serialized
model now drives a complete held-out SPI response on its inferred response pin;
noncausal programs remain valid data objects but are electrically quarantined.
