# COMPANION-LINK-001: Product UI Vocabulary

**Status:** version 1 integrated
**Date:** 2026-10-02

## Product boundary

A product board may attach a small companion MCU to the eight dedicated ASIC
inputs and eight dedicated ASIC outputs. The MCU owns buttons, LEDs, a display,
USB, and friendly text. It does not infer protocols, decide electrical safety,
or gain a path around the ASIC output-enable gates.

The eight bidirectional `uio` pads remain anonymous protocol pins. No protocol
pad is consumed by the product interface.

## What the fixed-direction pins already do

`ui[7:0]` is an eight-bit command or read-address byte. `uo[7:0]` is either the
always-visible fast status word or the selected read byte. This is a parallel
register protocol, not eight unrelated LEDs and buttons.

Normal command bits are:

| Bit | Meaning |
| ---: | --- |
| 0 | discover/capture |
| 1 | behavioral learn |
| 2 | promote model |
| 3 | grant ownership |
| 4 | activate model or launch one admitted probe |
| 5 | revoke immediately |
| 6 | clear fault and require recapture |
| 7 | status read when bit 4 is zero; contradiction when bit 4 is one |

The normal output word reports physical completion, direction, model, drive,
quiet, timing, contention, and rejected promotion as documented in
`docs/info.md`.

## Two status banks

During a passive status read, bits `{ui[1], ui[3:2], ui[6:5]}` select one of 32
pages and every command side effect is suppressed. Bit `ui[0]`, previously
ignored in this mode, now selects the bank:

- `ui[0]=0`: existing engineering pages, unchanged;
- `ui[0]=1`: stable companion-MCU vocabulary.

Bit `ui[4]` must remain zero. `companion_link.status_request()` is the reference
encoder. Reads are combinational; firmware should allow board-level settling
time after changing the input byte before sampling the output byte.

## Companion bank, version 1

| Page | Meaning |
| ---: | --- |
| `00` | identity byte `4D` (`M`) |
| `01` | identity byte `52` (`R`) |
| `02` | interface version `01` |
| `03` | product-state code |
| `04` | display/attention flags |
| `05` | recommended-next-evidence code |
| `06` | available button/action bitmap |
| `07` | raw normal status word |
| `08` | structural interpretation bitmap |
| `09` | knowledge/refusal reason |
| `0A` | safety/admission byte |
| `0B` | surviving interrogation-candidate count |
| `0C..1F` | reserved; reads as zero |

Product-state codes:

| Code | State |
| ---: | --- |
| `00` | reset |
| `01` | observing |
| `02` | quiet/waiting for traffic |
| `03` | ambiguous |
| `04` | discriminating probe ready |
| `05` | interrogating |
| `06` | resolved |
| `07` | executable model ready |
| `08` | actively emulating |
| `E0` | evidence compromised |
| `E1` | contradiction |
| `E2` | contention |
| `E3` | interrogation timeout |
| `E4` | revoked |

The flag byte, from bit 7 to bit 0, reports fault attention, user action
needed, passive recommendation, probe ready, model ready, active drive,
interrogation busy, and interrogation resolved.

The button/action byte, from bit 7 to bit 0, reports SPI promotion is presently
eligible, an interrogation is presently eligible, a proposal exists, ownership is required for active
work, clear-fault is applicable, revoke is applicable, authorize/probe is
implemented, and learn/start-over is implemented.

## Suggested physical controls

Two main buttons can be implemented entirely in companion firmware:

- **Learn / Start Over:** if necessary pulse clear-fault, then hold discovery
  or learning while the selected observation is collected.
- **Authorize / Probe Once:** assert ownership, then create exactly one rising
  edge on activate. Release activate before another action can occur.

A product should additionally provide a maintained **PASSIVE / ACTIVE** switch.
In PASSIVE, firmware withholds ownership and should also gate the external
analog ownership circuitry. Revocation remains available independently of the
display state.

`docs/THE-DECK-001.md` defines the complete reference state machine and the
important restriction on paged reads during continuous ownership.

## Display policy

The MCU may sleep or show no display during ordinary operation. A state change,
button press, proposal, or fault can wake it. Human text is a firmware concern:
for example, state `03` plus next-evidence `03` can render as “multiple models
fit; more distinguishing traffic is needed.” The byte vocabulary remains
stable even if the wording, display, or LED animation changes.

## Verification and cost

- The reference encoder round-trips all 32 addresses in both banks and proves
  that the resulting 64 input bytes are unique and never assert activate.
- The TinyTapeout-level test reads identity `MR` and interface version `01`.
- The full production source set passes strict Verilator lint.
- The Deck policy covers LISTEN discovery/learning, passive fault clear,
  edge-triggered promotion/probe/activation, maintained ownership, abort, and
  the prohibition on paged reads during active work.
- Generic Yosys synthesis reports 22,368 cells, 182 more than the preceding
  22,186-cell revision. A new physical run is still required before claiming
  post-layout cost or timing.
