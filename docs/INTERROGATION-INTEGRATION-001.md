# INTERROGATION-INTEGRATION-001: TinyTapeout Control Contract

**Status:** implementation target
**Date:** 2026-10-01

## Purpose

Integrate the adaptive open-drain learner into `mindreader_core` without
duplicating the existing shared-two-wire frontend or weakening the passive and
electrical-safety boundaries.

## Evidence path

Only a completed, unique, unsaturated `i2c_symbol_hypothesis` result becomes a
learner observation. The request is the decoded address byte without its
read/write bit. ACK is the observed low level in the ninth clock position.
Each completed observation window is admitted once. Protocol names, target
identity, expected response, and test truth have no RTL input path.

## Control reuse

The existing dedicated controls retain their meanings:

- `ui[3]` grants electrical ownership;
- a rising edge on `ui[4]` requests one action;
- `ui[5]` revokes authority immediately;
- `ui[6]` clears interrogation faults and requires passive recapture; and
- `ena=0`, reset, or contradiction also releases every pad immediately.

If a frozen SPI model exists, `ui[4]` belongs exclusively to that model. If no
frozen SPI model exists and a safe open-drain proposal is ready, one rising
edge starts exactly one interrogation transaction. `ui[4]` must return low
before another probe can be requested.

## Pad arbitration

SPI and interrogation are mutually exclusive owners. A frozen SPI model has
priority and makes the interrogation path ineligible. Otherwise only the
interrogation engine may reach the pad-output mux. The engine can drive only
zero or high impedance and only on the uniquely inferred clock/data pair.

No bitwise merging of two output-enable vectors is permitted. TinyTapeout
`ena` remains a final combinational gate after arbitration.

## Interrogation admission

A probe requires all of the following simultaneously:

1. at least one accepted passive shared-two-wire observation;
2. a unique, complete, unsaturated clock/data interpretation;
3. more than one surviving behavioral hypothesis;
4. a concrete discriminating proposal;
5. no frozen SPI model;
6. explicit ownership grant; and
7. no revoke, contradiction, timeout, or prior revocation fault.

Absence of any condition is a refusal, not permission to guess.

## Status pages

The four formerly reserved pages expose interrogation without changing normal
control behavior:

- `1C`: resolved, proposal-valid, busy, done, contradiction, timeout,
  revocation, and passive-evidence-seen;
- `1D`: surviving candidate count;
- `1E`: proposed seven-bit request; and
- `1F`: resolved-valid, inversion flag, winner bit, and accepted-evidence count.

## Required proof

The TinyTapeout-level test must start from raw anonymous pin traffic, obtain a
proposal through the integrated frontend, emulate a hidden target only through
resolved input pins, authorize individual probes, and reach the correct unique
model. It must also prove no drive before authorization, low-or-release output,
exclusive inferred-pin drive, one probe per activation edge, and immediate
release on revoke and `ena=0`.
