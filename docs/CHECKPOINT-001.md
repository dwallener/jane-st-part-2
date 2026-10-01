# CHECKPOINT-001: Passive Polyglot Frontend

**Status:** active  
**Opened:** 2026-10-01  
**Scope:** make the TinyTapeout-facing machine earn the right to propose an
active experiment by first broadening its passive electrical and protocol
evidence.

## Principle

Silence is evidence, not permission. An unknown quiet connection does not
reveal voltage convention, ownership, pin roles, or which transition might be
unsafe. The machine may report that evidence is insufficient and describe the
minimum useful experiment, but it must remain high impedance until electrical
constraints are known and ownership is explicitly granted.

## E. Observe all eight pins

- [x] **E1 Eight-pin quiet profiler.** Observe every bidirectional pin and
  declare quiet only after a complete programmable interval without any
  transition. Observation never changes an output-enable signal.
- [ ] **E2 Electrical-role evidence.** Retain per-pin activity, idle level,
  transition count, edge correlation, and candidate clock/control/data roles
  without prematurely choosing one interpretation.
- [ ] **E3 Inspectable evidence.** Make the activity mask, quiet state, evidence
  age, and overflow/insufficiency conditions available through a bounded status
  interface.

## F. Integrate passive protocol families

- [ ] **F1 Concurrent hypotheses.** Feed shared edge evidence to bounded SPI,
  UART, I2C, and generic-framing candidates.
- [ ] **F2 Family classification.** Report surviving families and genuine
  equivalence rather than forcing a single label.
- [ ] **F3 End-to-end held-out tests.** Exercise each integrated family through
  the TinyTapeout top with negative controls and malformed traffic.

## G. Propose before driving

- [ ] **G1 Missing-evidence diagnosis.** Distinguish quiet, insufficient,
  contradictory, and unsupported observations.
- [ ] **G2 Passive probe proposal.** Describe the smallest observation or
  transaction that would divide the surviving candidates without asserting
  output enable.
- [ ] **G3 Safety admission.** Require known electrical behavior, resolved pin
  roles, observed timing margin, explicit ownership, and explicit authorization
  before any proposal can become a transmission.

## H. First bounded interrogation

- [ ] **H1 Open-drain-only experiment.** Implement one I2C-class probe that can
  only pull a known line low or release it; it must never actively drive high.
- [ ] **H2 Immediate escape.** Bus activity, disagreement, timeout, revocation,
  reset, or TinyTapeout disable releases every output combinationally and
  latches an inspectable reason.
- [ ] **H3 Demonstration.** Show passive ambiguity, a proposed discriminating
  probe, explicit authorization, one safe observation, and reduced uncertainty.

## Current implementation boundary

The integrated ASIC top still performs autonomous behavioral learning only for
a bounded four-pin SPI-like family. UART and I2C frontends and the abstract
active-probe kernel exist in the broader repository evidence, but they are not
yet an eight-pin wire-facing polyglot machine. This checkpoint closes only when
the integrated top, tests, and documentation agree on that boundary.
