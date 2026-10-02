# Findings and Evidence Ledger

**Status:** living project record
**Established:** 2026-10-02
**Historical baseline:** `f1a8d4d`; later entries describe subsequent work

This file records how Protocol Doppelganger reached its present claims and what
the evidence actually supports. It is deliberately not a victory narrative.
Contradictions, negative results, superseded interpretations, and limits belong
here alongside successes.

## Update discipline

Update this ledger after any material inference result, architecture change,
new negative control, physical implementation run, or external evidence that
changes a claim. Each entry should identify:

1. the observation or executable artifact;
2. the derived result;
3. the claim it supports or weakens;
4. important alternatives that remain; and
5. the next discriminating check, if one exists.

Use these terms precisely:

- **Observed:** directly present in a capture, simulator result, build report,
  or inspected artifact.
- **Derived:** reproducibly calculated from observations.
- **Supported:** selected by cited evidence within explicit bounds.
- **Equivalent:** multiple descriptions remain but produce the same observed
  wire behavior.
- **Unresolved:** materially different explanations remain.
- **Refused:** the machine deliberately declines a conclusion or action.

Never collapse these distinct claims:

- a pattern is present in data;
- a decoder can represent it;
- a state is reachable under legal input;
- the behavior has been observed on the wire; and
- the machine has admitted the behavior for active execution.

## Historical progression

### 2026-09-30 — from emulator to protocol mindreader

- The repository began as a response to the Jane Street Protocol Emulator ASIC
  Competition and adopted the IHP CMOS5L TinyTapeout flow.
- A minimal CMOS5L smoke design established that the repository, Actions
  workflows, RTL simulation, and physical backend could work without replacing
  the existing general-purpose OpenROAD/Sky130 environment.
- The architecture moved beyond a programmable protocol engine to a passive
  learner: observe anonymous pins, infer timing and roles, preserve ambiguity,
  then execute only an admitted learned model.
- Cycle-delta traces, guarded timed transitions, provenance records, supervisor
  states, and saturation/contradiction semantics were developed as separate
  artifacts before integration.
- SPI became the first end-to-end learned family. Software and synthesizable RTL
  explored pin roles, select polarity, clock behavior, phase/order equivalence,
  word width, request/response templates, and held-out variations.
- The claim broadened from named protocols to structural classes. UART-like,
  shared-two-wire/I2C-like, and protocol-neutral event-framing hypotheses were
  added without granting them automatic authority to drive pins.
- Commit `f6b1f74` integrated the autonomous mindreader top. The claim at this
  point was bounded autonomous inference, not universal protocol recovery.

### 2026-10-01 — epistemic reporting, physical proof, and interrogation

- The first full IHP backend run passed, showing that the design was not merely
  simulator code. Later revisions cleaned synthesis and lint warnings rather
  than normalizing warning noise.
- Time-division multiplexing exposed a compact status/report interface without
  duplicating every analysis result at the pads.
- The knowledge report made uncertainty operational: conclusion, ambiguity,
  insufficiency, unsupported traffic, contradiction, compromised evidence,
  candidate-relative closure, and a recommended next observation.
- The project explicitly rejected the impossible claim that an unknown packet
  is known to be complete. It instead reports whether a candidate model saw its
  own required boundary and whether acquisition remained trustworthy.
- Active interrogation was designed behind a Chinese wall. Non-synthesizable
  host and open-drain bus models hide a randomly selected behavior; the learner
  sees only wire evidence. A synthesizable bounded learner chooses a request
  that divides surviving candidates.
- The open-drain interrogation path was integrated into the TinyTapeout top.
  It requires passive evidence, unique roles, a concrete proposal, ownership,
  and a fresh activation edge; it can only pull low or release.
- Commit `f1a8d4d` records working integrated interrogation and a viewable VCD.
  Randomized behavioral and raw-wire tests resolve supported invented targets
  or refuse exactly where no admitted action language exists.

### 2026-10-02 — artifact-audit discipline

Outcomes from the earlier Jane Street challenge prompted a deliberate audit
rule: inspect the boring artifacts as evidence. Timestamps, idle gaps, malformed
traffic, padding, reserved bits, headers, generated netlists, VCD metadata, and
layout reports are not secondary to the intended decoder path.

The first audit found a concrete trace-closure defect: the synthesizable edge
recorder retained edge deltas but did not expose the initial pin state or quiet
tail. Its records could therefore look internally consistent without being a
lossless replay witness. The current evidence-witness tranche adds those bounds
and compares the RTL stream against an independent Python reference across the
known-protocol corpus. All 13 canonical SPI, UART, and I2C waveforms plus a
quiet eight-pin negative control now match event for event and reconstruct
exactly; the complete experiment suite passes 129 tests. See
`docs/EVIDENCE-WITNESS-001.md`.

## Claims currently supported

- Anonymous activity on eight pins can feed concurrent bounded hypotheses for
  selected synchronous, asynchronous single-wire, shared two-wire, and generic
  event-framed traffic.
- The integrated design learns and executes a bounded SPI-like request/response
  family on an unknown legal subset of pins.
- Passive UART-like and I2C-like frontends preserve compatible interpretations
  and expose ambiguity instead of silently choosing a brand label.
- The generic framer provides candidate boundaries; it does not claim universal
  packet knowledge.
- For a bounded invented open-drain family, the machine can identify ambiguity,
  propose a discriminating request, safely interrogate a hidden target after
  explicit authorization, and reduce the candidate set.
- The design has passed RTL tests and at least one full CMOS5L physical flow.
  Backend success proves implementation feasibility for that revision, not
  electrical correctness of an external board or universality of inference.

## Open limits and future issues

- External voltage compatibility and analog/open-drain timing margins are board
  responsibilities and are not proven by digital RTL.
- Integrated unexpected-activity/disagreement escape remains incomplete.
- Protocol drift and concurrent independent protocols on disjoint pin groups
  are recorded in `docs/FUTURE-ISSUES-001.md`; neither is implemented.
- The admitted active language is intentionally narrow. Passive recognition of
  a family does not imply a safe probe exists for that family.
- Sampling above the chip clock and activity lost before capture begins are
  epistemically unavailable and must never be reported as observed absence.

## Deliberate audit checklist

Before declaring a milestone complete:

- compare at least two independent check paths where practical;
- replay or reconstruct the evidence rather than checking only a summary;
- inspect idle time, reset, malformed input, overflow, and truncation behavior;
- distinguish present, representable, reachable, observed, and admitted;
- search bounded parameter spaces for CRC/LFSR/scrambler/framing hypotheses
  where exhaustive checking is affordable;
- inspect human-readable constants, magic values, metadata, VCD headers, and
  physical artifacts for unintended or useful leakage; and
- record the strongest surviving alternative, not just the preferred result.

## Most recent experiment

**EVIDENCE-WITNESS-001:** the bounded RTL recorder now publishes baseline, every
delta/value/change record, quiet tail, completion, and overflow. An independent
Python reference derives the same witness and reconstructs all tested waveforms
exactly. This admits the record format for later architectural consideration;
it does not by itself justify spending top-level area on the FIFO.

The next audit target is the inference boundary: build adversarial traces whose
patterns are present and representable but are incomplete, unreachable, or not
safe to admit. Compare the software and RTL decisions, not merely their decoded
symbols, and retain every disagreement as a regression fixture.

## Product companion interface

The existing fixed-direction input and output banks now have an explicit
product role. The input byte carries commands or a passive read address; the
output byte carries fast status or the selected response. The previously
ignored `ui[0]` during status reads selects a second 32-page bank with a stable,
versioned MCU vocabulary. Identity, product state, attention flags,
recommendation, permitted buttons, safety, and interrogation summary are
available without consuming any of the eight anonymous protocol pins. See
`docs/COMPANION-LINK-001.md`. The complete experiment suite now passes 140
tests, the production RTL set passes strict Verilator lint, and generic
synthesis reports 22,368 cells—182 above the prior revision. Physical closure
for this addition has not yet been rerun.

The first product policy is now explicit in `docs/THE-DECK-001.md` and
`companion_controller.py`. It assigns LISTEN and JACK IN behavior from ASIC
state, models a maintained PASSIVE/ACTIVE authority switch, holds ownership
during active work, and refuses paged reads while continuous ownership is
required. That last constraint was exposed by working inward from the product:
status mode suppresses ordinary controls, so polling detailed pages during SPI
emulation would safely but undesirably remove the level-sensitive ownership
grant. Active firmware must watch the always-visible status word and go passive
before requesting detailed pages.

Working the controller into the end-to-end path exposed another distinction:
the merged passive report may remain structurally ambiguous while the bounded
SPI learner has enough causal, timing, and direction evidence to promote its
specific executable model. Companion button page bit 7 now reports that
promotion capability explicitly. The reference Deck controller and Cocotb top
test use the capability rather than guessing from the user-facing state label.
