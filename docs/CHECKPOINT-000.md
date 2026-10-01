# CHECKPOINT-000: Autonomous Mindreader Roadmap

**Status:** complete through “Broaden the claim”  
**Opened:** 2026-09-30  
**Closed:** 2026-09-30  
**Scope:** complete every gate through “Broaden the claim” before beginning
TinyTapeout product integration

## Meaning of complete

An item is complete only when its bounded claim is implemented, covered by a
negative control, included in the full regression, and described without
claiming capabilities outside the evidence. Documentation or a plausible demo
alone does not close a gate.

## A. Must-have architecture

- [x] **A1 Observe/takeover supervisor.** Reset is passive. Explicit states
  cover observation, candidate evaluation, admission, emulation, and fault.
  Contradiction, contention, reset, or revoked ownership returns every driver
  to high impedance.
- [x] **A2 RTL trace capture.** Anonymous pin changes and cycle deltas enter a
  bounded buffer. Overflow is sticky and invalidates evidence rather than
  silently truncating it.
- [x] **A3 On-chip physical inference.** A bounded SPI candidate set eliminates
  incompatible select polarity, clock idle level, sampling edge, and pin-role
  hypotheses while retaining real equivalence.
- [x] **A4 On-chip behavioral learning.** Decoded observations feed the RTL
  candidate-mask learner and produce an executable transition without a host
  constructing the response function.
- [x] **A5 Model promotion.** A frozen execution snapshot is admitted only when
  evidence, direction, causality, timing, and ownership gates pass.
- [x] **A6 Guard-decision analysis.** The model records when its request guard
  becomes decidable and whether any earlier driven bits are speculative.

## B. Complete the SPI path

- [x] **B1 Full mode/order/remap matrix.** Wire-level RTL covers modes 0–3,
  both representation orders, and permuted physical pins.
- [x] **B2 Timing-budget enforcement.** Observed select/setup and
  launch-to-sample intervals are compared with a configurable implementation
  requirement; inadequate models remain passive.
- [x] **B3 Contention detection.** Driven and observed response levels are
  compared when loopback evidence exists; disagreement releases the driver and
  latches a fault.
- [x] **B4 Transaction robustness.** Back-to-back, aborted, truncated,
  overlong, glitched-select, and reset-during-transfer cases have explicit
  outcomes.

## C. Make it a genuine mindreader

- [x] **C1 Autonomous proof.** Anonymous traffic enters RTL, produces a learned
  model, is promoted after ownership authorization, and answers a held-out
  request without host-generated model bytes.
- [x] **C2 Authorized active probe.** Hardware may propose a discriminating
  probe but cannot transmit until explicitly authorized; the observation feeds
  candidate elimination.
- [x] **C3 Stateful execution.** Multiple guarded transitions, current state,
  and state updates execute from a bounded model slot; unknown traffic cannot
  mutate state.
- [x] **C4 Provenance/status interface.** Evidence count, survivors,
  equivalence, contradictions, requested probe, admission state, and fault
  reason are externally inspectable.

## D. Broaden the claim

- [x] **D1 UART frontend.** Anonymous traffic yields polarity, bit period,
  width, parity/stop compatibility, and decoded symbols with ambiguity retained.
- [x] **D2 I²C frontend.** Start/stop, clock/data roles, bytes, ACK ownership,
  repeated starts, and open-drain constraints are represented and tested.
- [x] **D3 Adversarial invented protocols.** The suite includes variable width,
  length and delimiter framing, integrity rules, state, ambiguity, corrupted
  traces, and causally impossible behavior.
- [x] **D4 Honest benchmark report.** A generated report states stage reached,
  observations required, surviving equivalence, held-out generalization,
  replay result, refusal reason, and unsupported claims for every corpus case.

## Deferred until this checkpoint closes

- TinyTapeout control-plane pin assignment
- replacement of the smoke-test top module
- 6x4 physical resource closure
- GDS, precheck, and post-layout timing
- submission packaging and public demonstration polish

Those tasks remain important, but performing them before the architecture and
claim surface stabilize would optimize the wrong machine.

## Closure evidence

The closing regression ran 114 experiment and RTL tests, including held-out
generalization, insufficient-evidence and contradiction controls, unsafe-timing
promotion refusal, unauthorized-probe refusal and observed-answer candidate
elimination, exact adjacent SPI frames plus malformed boundaries, UART framing
rejection, repeated-start I²C, and all six adversarial cases. The original
TinyTapeout cocotb smoke test also passed independently.

Yosys synthesized and checked the updated active-probe controller and SPI
transaction decoder without structural errors. The live known-corpus scorer
reports eight SPI cases at `spi_symbols`, four UART cases at `uart_symbols`,
and one I²C case at `i2c_frames`. The generated honest benchmark contains all
nineteen known and invented cases and preserves ambiguity, refusal, replay
failure, and unsupported claims rather than converting them into successes.
