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
- [x] **E2 Bounded SPI electrical-role evidence.** Retain per-pin activity,
  baseline level, transition count, edge correlation, and candidate
  select/clock/data roles across all eight pins. A four-wire SPI link may
  occupy any subset; constant data or extra active pins remain unresolved.
- [x] **E3 Inspectable structural evidence.** Passive status pages expose
  the activity mask, quiet age, candidate classes, ambiguity/insufficiency, and
  clock-candidate mask without changing output enable.
- [x] **E4 Observation-integrity disclosure.** Report internal counter or
  storage saturation and candidate-relative incompleteness through the same
  externally visible refusal surface. End of an observation window is never
  treated as a universal packet boundary. Sampling aliasing above the chip
  clock remains inherently unknowable and is documented rather than hidden.

## F. Integrate passive protocol families

- [x] **F1 Structural hypothesis routing.** Feed one shared eight-pin evidence
  window to nonexclusive asynchronous-single-wire, selected-synchronous, and
  shared-two-wire candidate routes. Canonical SPI, UART, and I2C traces plus a
  quiet negative control reach their expected structural routes.
- [x] **F2 Concurrent symbol hypotheses.** Feed routed evidence into bounded
  SPI, UART, I2C, and generic-framing symbol/frame candidates. The first
  wire-facing UART bank is integrated: it concurrently retains compatible
  pin, idle polarity, bit-period, width, parity, and stop-count hypotheses.
  An online shared-two-wire bank now eliminates directed clock/data candidates
  on every observation and recognizes start, byte/ACK groups, and stop. A
  protocol-neutral event framer concurrently retains control-enclosure,
  quiet-gap, and repeated-event-count boundaries.
- [x] **F3 Family classification.** Merge every ready inference surface into a
  six-bit interpretation mask and independently report unique, equivalent, or
  insufficient. The result uses structural meanings rather than protocol
  brand names.
- [x] **F4 End-to-end held-out tests.** The TinyTapeout top exercises learned
  selected-synchronous execution, UART-like and shared-two-wire discovery,
  generic ambiguity, silence, incomplete selected traffic, multi-pin UART
  contamination, missing two-wire STOP, and unequal event bursts. Every
  passive refusal case requires all output enables low.

## G. Propose before driving

- [x] **G1 Missing-evidence diagnosis.** A machine-readable knowledge report
  distinguishes observation in progress, conclusion, ambiguity,
  insufficiency, unsupported traffic, contradiction, and compromised
  evidence. A separate reason code distinguishes quiet, an open candidate
  boundary, multiple survivors, no supported model, saturation, and
  contradiction.
- [ ] **G2 Passive probe proposal.** Describe the smallest observation or
  transaction that would divide the surviving candidates without asserting
  output enable. The first advisory layer is implemented: continue passive
  observation, observe a boundary, seek differentiating traffic, verify
  electrical constraints, request authorization, recapture, or review an
  unsupported trace. It does not yet synthesize a concrete discriminating
  waveform.
- [ ] **G3 Safety admission.** Require known electrical behavior, resolved pin
  roles, observed timing margin, explicit ownership, and explicit authorization
  before any proposal can become a transmission. The report now publishes the
  implemented SPI admission gates and whether its recommendation is passive;
  connecting a future generated probe remains open.

## H. First bounded interrogation

- [ ] **H1 Open-drain-only experiment.** Implement one I2C-class probe that can
  only pull a known line low or release it; it must never actively drive high.
  The standalone randomized kernel is implemented and verified; integration
  behind the TinyTapeout-facing admission boundary remains open.
- [ ] **H2 Immediate escape.** Bus activity, disagreement, timeout, revocation,
  reset, or TinyTapeout disable releases every output combinationally and
  latches an inspectable reason. The kernel now covers authorization,
  revocation, stuck-clock timeout, reset, and low-or-release enforcement;
  integrated unexpected-activity and TinyTapeout-disable tests remain open.
- [ ] **H3 Demonstration.** Show passive ambiguity, a proposed discriminating
  probe, explicit authorization, one safe observation, and reduced uncertainty.
  A Chinese-wall simulation resolves sixteen randomized two-candidate targets,
  but its candidate pair is not yet generated by the integrated passive path.

## Current implementation boundary

The integrated ASIC top performs autonomous behavioral learning for a bounded
four-wire SPI-like family appearing on an unknown subset of the eight pins. A
passive UART-like bank now observes an unknown single pin and reports every
compatible bounded symbol interpretation. A passive shared-two-wire bank
incrementally identifies clock/data roles and byte/ACK framing. Neither bank
yet learns behavior or transmits. The abstract active-probe kernel exists only
in the broader repository evidence. This
checkpoint closes only when the integrated top, tests, and documentation agree
on that boundary. It now also exposes a compact epistemic interface: what is
known, why inference stopped, what evidence to seek next, candidate-relative
closure, acquisition integrity, and active-admission state.

## Deferred issues

`FUTURE-ISSUES-001.md` records two deliberately unsupported extensions for a
later checkpoint: revising a model when the protocol changes over time, and
separating multiple protocols operating concurrently on different pin groups.
