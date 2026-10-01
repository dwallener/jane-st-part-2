# CORPUS-000: Known-Protocol Trick Bag

**Status:** first golden waveform tranche implemented  
**Date:** 2026-09-30  
**Decision gate:** stop optimizing only for synthetic fixtures designed around
the current learner

## Honest baseline

Before this tranche, every executable experiment used a controlled synthetic
protocol. Those fixtures are valuable because each isolates one hypothesis,
but they do not demonstrate compatibility with established protocols. The
project did not yet have a known-protocol trick bag.

## Benchmark contract

Each case contains two deliberately separated artifacts:

1. an anonymous cycle-sampled waveform containing only a pin count and indexed
   digital levels; and
2. scorer-only truth containing the protocol family, pin roles, conventions,
   and expected symbols.

The inference API returns only the first artifact. Names such as `clock`,
`select`, `UART`, and `I2C` cannot leak into the learner.

Reference encoders and decoders validate each other before a case is admitted.
This does not prove that Doppelganger can infer the case; it proves that the
benchmark stimulus and truth agree.

## Initial tranche

The first 13 cases cover:

| Family | Cases | Variations |
| --- | ---: | --- |
| SPI | 8 | modes 0–3, MSB-first and LSB-first, simultaneous request/response |
| UART | 4 | 8N1, LSB-first, values `00`, `55`, `A5`, and `FF` |
| I²C | 1 | 7-bit address `0x50`, write, address/data ACK, start and stop |

These are protocol-conformant reference waveforms at the limited behaviors
listed. They are not complete implementations of their respective standards.

## Why these three

- SPI tests externally clocked synchronous framing, four edge conventions,
  explicit selection, and simultaneous directions.
- UART removes the clock pin and requires timing recovery from an asynchronous
  line with idle, start, data, and stop roles.
- I²C introduces open-drain-style shared signaling, in-band ACK bits, start and
  stop conditions, and a ninth clock beyond each data byte.

Together they are structurally different enough to expose an architecture
that has quietly specialized itself to the synthetic selected serial link.

## What passes today

All 13 fixtures round-trip through independent reference decoders. No claim is
yet made that the inference pipeline recognizes them. The current physical
learner assumes separate request/response data and explicit response-valid, so
UART and I²C are expected to fail. Those failures are useful architecture
evidence, not regressions to hide.

The waveform adapter now converts every case into a lossless anonymous
delta-edge trace, including otherwise easy-to-lose trailing idle time. All 13
cases pass capture and per-pin activity profiling.

The honest current failure matrix stops every case at `activity_profile`:

| Family | Current frontend mismatch |
| --- | --- |
| SPI | Requires active-high select and a separate response-valid phase; SPI has active-low selection and simultaneous data. |
| UART | Requires external clock and select pins; UART recovers timing from one asynchronous line. |
| I²C | Requires separate request and response pins; I²C uses shared bidirectional open-drain data and in-band ACK. |

This exposes a real overfit: the component learners are broader than replay,
but the synthetic-link frontend connecting them is highly specific.

## Known versus invented protocols

The corpus will maintain two visibly separate suites:

- **canonical:** established protocols with independently checked golden
  waveforms and scorer-only truth;
- **synthetic/adversarial:** invented protocols designed to isolate ambiguity,
  compose unusual features, or sit just outside a hypothesis boundary.

Both are useful. Only the canonical suite supports claims about compatibility
with protocols we did not design around the learner. Synthetic cases support
falsification, coverage, and architectural exploration.

## Planned tranches

Future additions should be admitted only with golden decoding and a specific
reason for inclusion:

- SPI multiword transfers, variable word widths, and select gaps;
- UART 7E1, baud variation, jitter, back-to-back bytes, and framing errors;
- I²C reads, NACK, repeated start, clock stretching, and multiple data bytes;
- delimiter and stuffing families such as SLIP, HDLC-style flags, and COBS;
- SMBus PEC, Modbus CRC-16, and representative sensor/register protocols;
- adversarial mutations that deliberately create ambiguous explanations.

## Scoring ladder

Each case should eventually report the deepest successful layer:

```text
capture -> pin roles -> timing -> symbols -> frames -> fields
        -> integrity -> behavior -> executable emulation
```

A family name is never an inference target. Success means producing an
equivalent executable description, not recognizing the label "SPI."

## Immediate next step

Replace the selected-serial assumptions with topology families rather than
special cases. SPI is the smallest next target: infer active select polarity,
clock idle level and sampling edge, two simultaneous data pins, and the known
bit-order equivalence. UART and I²C should remain explicit unsupported results
until their distinct topology engines exist.
