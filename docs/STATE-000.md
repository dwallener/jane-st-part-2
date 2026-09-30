# STATE-000: Two-State Toggle Hypothesis

**Status:** implemented for Experiment 002  
**Date:** 2026-09-30

## Question

Can the learner distinguish a peripheral whose response depends on prior
traffic from a stateless request/response table, and can it generalize a held-
out payload in both inferred states?

## Supplied structure

Experiment 002 is intentionally bounded. The learner is given several
transaction sequences with a known reset boundary before each sequence. It is
also given the following hypothesis class:

- exactly two states;
- reset enters state zero;
- one exact request toggles the state after producing its response;
- the toggle request has one fixed response and delay;
- all other requests are described by one mask/template model per state; and
- unsupported or ambiguous behavior returns `UNKNOWN`.

The identity of the toggle request, both per-state response templates, and all
response delays are learned from observations. Hidden state labels are not
included in the evidence.

## Synthetic peripheral

The peripheral recognizes:

- `0xF0`: return `0x0F` after four cycles, then toggle state;
- `0xA?` in state zero: return `0x6?` after six cycles;
- `0xA?` in state one: return `0xE?` after six cycles.

The low response nibble copies the request payload. Training includes requests
from both states but excludes `0xA7`.

The held-out sequence is:

```text
reset
0xA7 -> 0x67 after 6 cycles
0xF0 -> 0x0F after 4 cycles
0xA7 -> 0xE7 after 6 cycles
0xF0 -> 0x0F after 4 cycles
0xA7 -> 0x67 after 6 cycles
```

## Candidate selection

Every observed exact request is considered as a possible toggle. A candidate
survives only if:

1. its observed response is consistent;
2. it partitions non-control evidence into two nonempty states;
3. both state partitions produce complete mask/template models;
4. both models recognize the same request family;
5. the proposed control request is outside that data family;
6. both models reproduce every observation assigned to them; and
7. at least one identical request has different observed behavior across the
   two inferred states.

The result is executable only when exactly one candidate survives. Zero or
multiple candidates are reported as ambiguous.

## What this proves—and does not

Passing demonstrates history-dependent emulation, transition inference within
a declared bounded hypothesis class, and held-out field generalization in two
states. A stateless replay table cannot represent the corpus because identical
requests have conflicting responses.

It does not discover the number of states, arbitrary transition predicates,
reset behavior, or the hypothesis class itself. Those remain later work.

