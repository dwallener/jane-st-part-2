# TT-INTEGRATION-000: Autonomous Mindreader Tapeout Candidate

**Status:** RTL-integrated and locally verified  
**Date:** 2026-09-30

The disposable counter smoke test has been removed from `mindreader_core.v`.
The TinyTapeout top now contains the bounded autonomous SPI mindreader itself:

- anonymous four-wire physical inference across any four of eight pins;
- exact eight-bit transaction decoding;
- simultaneous learning in both possible data directions;
- guarded model promotion and frozen execution state;
- observed timing admission;
- ownership, activation, revocation, and contradiction controls;
- stream-causal wire response; and
- pad-loopback contention detection with immediate output-enable release.

All eight `uio` pins feed both the passive quiet detector and bounded SPI
physical learner. The eight dedicated inputs control
discovery, learning, promotion, ownership, activation, revocation, fault clear,
and contradiction injection. The eight dedicated outputs expose physical,
direction, model, drive, quiet, timing-admission, contention, and promotion
status. The complete mapping is recorded in `info.yaml` and `docs/info.md`.
Passive status pages additionally expose shared taxonomy evidence: activity,
quiet age, nonexclusive structural routes, ambiguity/insufficiency, clock
candidates, and UART-like symbol candidates. Reading these pages suppresses
ordinary control side effects and cannot affect output enable.

The TinyTapeout cocotb test exercises the complete product boundary. It learns
from one physical-discovery frame and eight behavioral frames, refuses an
unauthorized promotion, admits an authorized model, emits `0x63` for unseen
request `0xA7`, releases the response pin on contention, latches the fault, and
proves that `ena=0` disables every output path.

The closing local checks passed:

- 114 experiment and component RTL tests;
- the complete TinyTapeout top-level cocotb test;
- Yosys hierarchy, synthesis, and structural checks; and
- 5,665 generic synthesized cells before CMOS5L technology mapping for the
  original four-pin integration.

The eight-pin subset-search revision synthesizes to 7,558 generic cells, an
increase of 1,893 cells. Yosys hierarchy and structural checks report no
problems. The previous revision occupied 9.55% of the 6x4 CMOS5L standard-cell
area; the widened revision requires a new backend run before claiming a routed
utilization or timing result.

Adding the passive structural-hypothesis router and its first status pages raises the
generic count to 8,037 cells. The additional 479 cells buy shared per-pin edge
evidence, three nonexclusive structural routes, explicit ambiguity and
insufficiency, and externally readable activity/clock masks. This remains a
synthesis estimate; routed CMOS5L results are intentionally not projected from
the generic count.

The first integrated UART-like candidate bank adds unknown one-of-eight pin
selection, idle-polarity inference, periods from 2 through 16 clocks, widths
from 5 through 9 bits, three parity modes, and one or two stop bits. A naive
fully parallel enumeration synthesized to 9,978 cells for the UART block and
18,164 cells overall. The retained implementation reuses one evaluator for 450
clocks after capture. It synthesizes to 2,895 cells for the UART block and
11,072 cells overall: 7,092 cells removed without reducing the hypothesis
space. Yosys reports zero structural problems and no inferred latches. A new
CMOS5L backend run is still required before making any routed fit claim.

The current local regression passes 119 experiment/component tests, 68
parameterized subtests, and all five TinyTapeout top-level cocotb scenarios. The
second top-level scenario identifies a normal-idle 8N1-compatible trace on
physical pin 3 while proving that neither the SPI-complete bit nor any output
enable can assert.

The online shared-two-wire bank evaluates directed clock/data assignments on
every observed sample and synthesizes to 8,555 generic cells, bringing the
complete design to 19,731 cells. This is intentionally a parallel first
implementation: it establishes live elimination semantics before consolidating
state storage. The third top-level scenario uniquely identifies clock pin 2
and data pin 5 from an acknowledged two-byte write while remaining passive.

The protocol-neutral event framer adds 543 cells locally and raises the full
design to 20,463 generic cells including the expanded status mux. It retains
two-edge control enclosure, quiet-gap separation, and repeated event-count
framing simultaneously. The fourth top-level scenario exposes genuine
gap/fixed-count ambiguity while remaining passive. Yosys again reports zero
structural problems and no inferred latches.

The merged equivalence classifier itself is 32 generic cells; the classifier
plus two additional status pages raise the complete design to 20,552 cells.
It reports six structural interpretations and distinct ready, unique,
equivalent, and insufficient outcomes. The fourth top-level scenario waits for
all inference surfaces and observes exactly the two intended generic survivors.

The fifth top-level scenario is a refusal matrix. Silence reports
insufficiency; an incomplete selected frame never resolves; a UART-like trace
with a second active pin refuses pin identity; a shared-two-wire trace without
STOP yields no candidate; and unequal bursts eliminate only the fixed-count
interpretation. All five cases require `uio_oe == 0` throughout.

The generic count is not a placement result. Fit, routed timing, DRC, precheck,
and gate-level behavior must be decided by the TinyTapeout CMOS5L backend.
