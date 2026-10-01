# KNOWLEDGE-RTL-001: Evidence Adequacy and Next Observation

**Status:** first machine-readable advisory interface integrated
**Date:** 2026-10-01

The chip's purpose is not merely to attach a protocol name to traffic. It is an
uncertainty-aware protocol reconnaissance engine: observe without disturbing,
retain plausible interpretations, disclose limitations in the observation,
explain why it cannot yet decide, and recommend the next evidence to collect.

## Epistemic boundary

An unknown protocol cannot provide a universal `packet_complete` signal. The
hardware therefore reports three separate facts:

1. **Observation integrity:** whether its own bounded counters or storage
   saturated. This says whether the hardware discarded representable detail.
2. **Observed boundary evidence:** select release, UART-compatible stop,
   shared-two-wire STOP, control enclosure, or a quiet gap.
3. **Candidate-relative closure:** which surviving interpretations regard the
   observed material as closed. A trace may be complete for one candidate and
   incomplete—or an arbitrary prefix of a stream—for another.

Ending the host-selected capture window is not boundary evidence. Likewise,
the synchronous sampler cannot know whether input transitions occurred between
clock samples. The report makes no claim about events beyond its sampling
bandwidth.

## Machine-readable report

`protocol_knowledge_reporter.v` produces four byte codes. TinyTapeout status
pages add candidate-closure and per-collector integrity detail.

Knowledge states:

| Code | Meaning |
| --- | --- |
| `00` | observation or evaluation still in progress |
| `01` | one supported interpretation remains with candidate-relative closure |
| `02` | multiple interpretations remain |
| `03` | evidence is insufficient |
| `04` | bounded recognizers do not support the observed closed structure |
| `05` | evidence contradicts an admitted model |
| `06` | internal evidence capacity was exceeded; conclusions are poisoned |

Reason codes:

| Code | Meaning |
| --- | --- |
| `00` | no refusal reason |
| `01` | observation/evaluation in progress |
| `02` | quiet connection supplied no traffic |
| `03` | no supported candidate has observed closure |
| `04` | multiple candidates remain |
| `05` | closed evidence matches no supported model |
| `06` | a bounded counter or store saturated |
| `07` | contradiction with an admitted model |

Next-evidence codes:

| Code | Recommendation |
| --- | --- |
| `00` | no additional evidence requested |
| `01` | continue passive observation |
| `02` | observe a candidate boundary |
| `03` | observe traffic that distinguishes survivors |
| `04` | verify electrical roles and timing |
| `05` | request explicit ownership/authorization |
| `06` | reset and recapture within capacity |
| `07` | retain the trace for unsupported-model analysis |

These are recommendations, never commands. In particular, code `05` does not
grant authority and no knowledge-report output is connected to pad output
enable.

## Safety byte

The safety byte reports, from bit 7 to bit 0: recommendation is passive,
active action prohibited, roles resolved, timing admissible, ownership granted,
executable model ready, some candidate-relative closure exists, and all
currently implemented active-admission gates pass.

The closure byte assigns bits 0–5 to UART-like, selected-synchronous,
shared-two-wire, control-enclosed, gap-delimited, and fixed-event-count
interpretations. These bits deliberately may coexist.

The integrity byte assigns bit 6 to aggregate saturation; bits 5–1 identify
router, UART, shared-two-wire, generic-framer, and SPI-role saturation; bit 0
records a candidate-relative incomplete SPI transaction. Saturation has
priority over every apparent conclusion and recommends recapture.

## Verification

The component test covers every knowledge state used by the first integration,
the recommendation transition from passive evidence gathering through active
admission, and precedence of saturation and contradiction. The TinyTapeout
test drives more transitions than the bounded collectors can retain and checks
that the external pages report compromised evidence, saturation, recapture,
and high-impedance protocol pins.
