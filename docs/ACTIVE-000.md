# ACTIVE-000: Bounded Active Disambiguation

**Status:** implemented for Experiment 003  
**Date:** 2026-09-30

## Question

When passive observations support several response templates, can the system
identify a useful experiment instead of guessing which template is correct?

## Starting ambiguity

The stateless synthetic peripheral from Experiment 000 returns
`0x60 | request[3:0]` for the `0xA?` request family.

Experiment 003 initially observes only `0xA0` and `0xAF`. Those examples prove
that each low response bit follows some low request bit, but all four request
bits changed together. There are 256 distinct copy templates consistent with
the evidence. Selecting the intended bit mapping at this point would be an
unsupported guess.

## Candidate representation

The bounded hypothesis expander takes every response-bit expression retained
by the existing learner and forms the Cartesian product of those choices. It
has an explicit maximum candidate count and refuses to expand an unbounded
space. Each resulting candidate is an executable mask/template model.

## Probe selection

For every allowed, unobserved request accepted by all candidates:

1. execute the request against every candidate;
2. partition candidates by predicted timed response;
3. measure the largest remaining partition; and
4. choose the request that minimizes that worst case.

Ties prefer more distinct outcomes and then the numerically smallest request.
This makes selection deterministic and exposes both the expected split and its
worst case. The selected request is a proposal; policy or host approval remains
outside this experiment.

## Update rule

After the real peripheral supplies a timed response, retain exactly the
candidates that predicted it. Zero survivors mean the evidence contradicts the
hypothesis language. One survivor resolves the model. Multiple survivors cause
another probe proposal.

## Success criteria

- Sparse evidence remains a set of 256 candidates rather than becoming a
  fabricated single model.
- Every proposed request is within the learned `0xA?` family and has not
  already been observed.
- Repeated proposed probes converge to one model against the synthetic
  peripheral.
- The resolved model answers an unseen request correctly.
- Contradictory evidence produces zero candidates.
- Behaviorally indistinguishable candidates produce no fake separating query.

## Non-claims

This experiment does not determine whether a probe is electrically or
operationally safe, discover an unrestricted query language, or guarantee that
an arbitrary candidate set can be separated. The candidate expansion is a
software oracle; hardware must eventually use a far more compact uncertainty
representation.

