# THE-DECK-001: Mindreader Product State Machine

**Status:** reference policy implemented
**Date:** 2026-10-02

## The object

The product is **The Deck**: a pocket protocol-reconnaissance instrument. It
sits electrically quiet beside an unfamiliar digital conversation, develops a
bounded account of what it sees, tells the operator what remains uncertain,
and—only after a physical act of consent—asks one question or takes the place
of the learned peripheral.

The industrial-design fantasy may be cyberdeck; the safety language must stay
literal. Animation and color may say “future.” Faults still say `CONTENTION`,
`EVIDENCE LOST`, or `REVOKED`, not a cute euphemism.

## Architecture

```text
buttons, ACTIVE switch, light, display, USB
                    |
               companion MCU
        presentation and sequencing only
                    |
       ui[7:0] commands / uo[7:0] reports
                    |
              Mindreader ASIC
       evidence, inference, admission, timing
                    |
          uio[7:0] anonymous protocol pins
```

The MCU may translate and sequence ASIC decisions. It must not invent a
protocol conclusion, clear evidence loss from the display, emulate timing in
software, or bypass ASIC output-enable admission.

## Physical controls

The first product has two momentary buttons and one maintained switch:

- **LISTEN** — begin or continue passive acquisition. In a fault state it first
  requests clear-and-recapture. If physical roles are unknown it selects
  discovery; after roles are known it selects behavioral learning.
- **JACK IN** — context-sensitive but never ambiguous on screen. It promotes a
  resolved executable model, launches exactly one admitted probe, activates a
  frozen model, or revokes an operation already in progress.
- **PASSIVE / ACTIVE** — a maintained authority switch. Moving to PASSIVE
  asserts revoke and should independently disable external analog ownership.
  ACTIVE merely permits the MCU to request ownership; it does not itself drive
  a protocol pin.

The display must show the impending meaning of JACK IN before accepting it:
`PROMOTE MODEL`, `ASK ONE QUESTION`, `BEGIN EMULATION`, or `ABORT`.

## User-visible states

| ASIC code | Deck label | Light | Meaning |
| ---: | --- | --- | --- |
| `00` | BOOT | dim white | ASIC reset |
| `01` | LISTENING | blue pulse | collecting or evaluating evidence |
| `02` | SILENCE | blue slow pulse | no useful traffic yet |
| `03` | FORK | amber | materially different explanations remain |
| `04` | QUESTION READY | violet | one bounded probe can divide survivors |
| `05` | ASKING | violet pulse | one authorized interrogation is active |
| `06` | LOCK | green | one supported result remains |
| `07` | GHOST READY | green pulse | executable model is frozen but passive |
| `08` | GHOSTING | green solid | ASIC is actively emulating |
| `E0` | EVIDENCE LOST | red | bounded acquisition saturated |
| `E1` | CONTRADICTION | red | observation disagrees with admitted model |
| `E2` | CONTENTION | red flash | driven and observed electrical levels differ |
| `E3` | TIMEOUT | red | bounded interrogation did not complete |
| `E4` | REVOKED | amber/red | authority was withdrawn |

The expressive labels are presentation aliases for stable numeric ASIC states.
Logs and diagnostic screens always retain the literal engineering meaning.

## Control policy

The reference policy is implemented in `companion_controller.py`.

### LISTEN

- While held, use `DISCOVER` until physical inference is complete.
- Thereafter use `LEARN` to accumulate behavioral evidence.
- In a fault state, its rising edge sends `CLEAR_FAULT`; subsequent held cycles
  restart discovery.
- LISTEN never asserts ownership.

### JACK IN

- When the explicit promotion-ready capability is set, assert ownership and
  pulse `PROMOTE`. This capability may coexist with `FORK`: ambiguity among
  passive structural labels does not necessarily invalidate the admitted
  bounded SPI model.
- At `QUESTION READY`, assert ownership and create one `ACTIVATE` edge.
- At `GHOST READY`, assert ownership and create one `ACTIVATE` edge.
- At `ASKING` or `GHOSTING`, assert `REVOKE` instead.
- In any other state, do nothing and explain why.

The action is edge-triggered. Holding the button cannot issue repeated probes.

### Maintained authority

During `ASKING` or `GHOSTING`, the MCU continuously holds ownership. Dropping
the ACTIVE switch or losing MCU confidence asserts revoke. The physical switch
should also have a hardware path to external isolation so firmware is not the
sole authority boundary.

## Reporting schedule

When passive, the MCU may poll the companion status bank and wake the display
only on a state or attention change. During active emulation, entering status
mode would temporarily remove the level-sensitive ownership grant. Therefore:

- do not issue paged reads while continuous ownership is required;
- monitor the always-visible normal output byte instead; and
- revoke/go passive before requesting detailed diagnostic pages.

This is intentional fail-safe behavior, not a firmware inconvenience. A later
ASIC revision may add a latched snapshot or interrupt sequence if continuous
detailed telemetry earns the area and verification cost.

## Firmware loop

```text
sample physical controls
sample normal ASIC status

if switch moved to PASSIVE:
    assert REVOKE immediately
else:
    emit the reference policy command for LISTEN/JACK-IN edges

if ASIC does not require continuous ownership:
    poll identity, state, flags, recommendation, and reason
    update display only if the semantic snapshot changed
else:
    keep OWNERSHIP asserted
    watch immediate fault/drive bits on the normal output byte
```

## Expansion path

The versioned companion bank leaves twenty pages reserved. Plausible future
uses include a monotonic event sequence, compact trace streaming, multiple-link
selection, protocol-drift notices, model export, and an MCU interrupt reason.
None should be added until its authority and evidence semantics are explicit.
