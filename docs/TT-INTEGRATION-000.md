# TT-INTEGRATION-000: Autonomous Mindreader Tapeout Candidate

**Status:** RTL-integrated and locally verified  
**Date:** 2026-09-30

The disposable counter smoke test has been removed from `mindreader_core.v`.
The TinyTapeout top now contains the bounded autonomous SPI mindreader itself:

- anonymous four-pin physical inference;
- exact eight-bit transaction decoding;
- simultaneous learning in both possible data directions;
- guarded model promotion and frozen execution state;
- observed timing admission;
- ownership, activation, revocation, and contradiction controls;
- stream-causal wire response; and
- pad-loopback contention detection with immediate output-enable release.

All eight `uio` pins now feed a passive quiet detector; the bounded SPI learner
continues to consume `uio[3:0]`. The eight dedicated inputs control
discovery, learning, promotion, ownership, activation, revocation, fault clear,
and contradiction injection. The eight dedicated outputs expose physical,
direction, model, drive, quiet, timing-admission, contention, and promotion
status. The complete mapping is recorded in `info.yaml` and `docs/info.md`.

The TinyTapeout cocotb test exercises the complete product boundary. It learns
from one physical-discovery frame and eight behavioral frames, refuses an
unauthorized promotion, admits an authorized model, emits `0x63` for unseen
request `0xA7`, releases the response pin on contention, latches the fault, and
proves that `ena=0` disables every output path.

The closing local checks passed:

- 114 experiment and component RTL tests;
- the complete TinyTapeout top-level cocotb test;
- Yosys hierarchy, synthesis, and structural checks; and
- 5,665 generic synthesized cells before CMOS5L technology mapping.

The generic count is not a placement result. Fit, routed timing, DRC, precheck,
and gate-level behavior must be decided by the TinyTapeout CMOS5L backend.
