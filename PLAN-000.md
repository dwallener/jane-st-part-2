# PLAN-000: Prove the Idea Before Designing the Chip

**Status:** proposed  
**Date:** 2026-09-30  
**Competition deadline:** 2027-01-18  
**Current phase:** feasibility; no architecture has been selected

## Objective

Decide quickly and honestly whether Protocol Doppelganger can become a real
ASIC submission with a claim stronger than record/replay:

> The chip observes a device, learns a bounded timed behavioral model, and
> later produces a correct response to at least one valid exchange that was not
> captured verbatim during training.

The first plan is designed to answer three questions in order:

1. Can we reproduce the specified IHP CMOS5L flow reliably?
2. Can a deliberately small learner demonstrate genuine generalization?
3. Can the useful part of that learner fit in the available silicon and operate
   within protocol response deadlines?

We will not commit to an instruction set, RTL language, SRAM organization, or
full chip architecture until those questions have evidence-backed answers.

## Adopted development strategy

Tiny Tapeout defines the boundary; it does not define the machine.

We will perform one early, isolated CMOS5L smoke test, freeze a thin Tiny
Tapeout wrapper and pin budget, and then return to a fast development loop built
around a reference model and portable synthesizable Verilog. Full hardening is
not the daily test loop. It returns at architectural milestones and as soon as
the memory strategy becomes concrete.

### CI dispatch policy

As of 2026-09-30, ordinary pushes run the fast RTL and documentation checks but
do not automatically launch the full CMOS5L physical-design flow. The `gds`
workflow is manual (`workflow_dispatch`) and is started deliberately from the
GitHub Actions interface or with:

```sh
gh workflow run gds.yaml
```

This policy prevents routine commits from starting synthesis, place-and-route,
precheck, gate-level simulation, and Pages deployment. Run the physical flow
after changes to the top-level boundary, clock/reset assumptions, memory
implementation, hardening configuration, or at an explicit architecture
milestone. The fast RTL workflow remains the required check on normal pushes.

```text
reference model
      <-> differential tests
portable synthesizable core
      |
thin Tiny Tapeout wrapper
      |
CMOS5L synthesis, place-and-route, precheck, and submission
```

## Guiding principles

1. **Inference is the project.** UART, SPI, and I2C support are mandatory
   baseline demonstrations, not the reason to build the chip.
2. **The claim must be falsifiable.** A held-out exchange must distinguish
   learning from exact trace replay.
3. **Unknown must remain unknown.** Rejecting an unsupported request is better
   than an impressive-looking incorrect response.
4. **The host may assist, but not perform the central trick.** At least one
   complete learn-and-emulate path must work without host-side inference.
5. **Synthesis starts early.** Software elegance is irrelevant if the model or
   matcher does not fit.
6. **The official CI flow is the reference.** Local tooling must reproduce it,
   not silently substitute nearby versions.
7. **Every phase has an exit.** We stop or narrow the claim when evidence fails
   a gate; we do not rescue the project with branding.
8. **The wrapper stays boring.** Learning, timing, and protocol behavior belong
   in a portable core; the `tt_um_*` module only maps the fixed interface.
9. **Hardening is a milestone test.** Fast simulation drives ordinary
   development. CMOS5L hardening checks physical assumptions when they change.

## Fixed external constraints

From the competition announcement and current CMOS5L support branches:

- Process: IHP 130 nm CMOS5L.
- Allocation: 6x4 Tiny Tapeout tiles; 8x4 is possible only if officially
  announced.
- Nominal area: approximately 0.7 mm² for 6x4.
- Rough logic guidance: approximately 1K cells per tile, before routing and
  clock-tree realities.
- Required character: open source, general-purpose protocol emulation.
- Baseline protocols: UART, SPI, and I2C.
- Stretch protocols: low-speed USB and 10 Mbit Ethernet.
- Submission deadline: 2027-01-18.

The actual usable cell count, SRAM macro geometry, maximum clock, and routing
margin are unknown until we run the target flow. Estimates are not budgets.

## Workstreams

Four workstreams proceed in parallel conceptually, but each has a dependency
gate before it can consume substantial implementation time.

### T — Toolchain and physical reality

Reproduce the competition's CMOS5L build, measure the real tile, and establish
a deterministic hardening workflow on the isolated machine.

### L — Learning claim and software oracle

Define the smallest useful hypothesis language, implement it in software, and
show held-out generalization on controlled and real traces.

### H — Hardware kernel

Implement and synthesize only the primitives proven necessary by the software
oracle: capture, timing, matching, state update, response scheduling, and a
bounded amount of learning.

### D — Demonstration and verification

Design the flagship experiment, uncertainty behavior, reproducible tests, and
formal properties at the same time as the architecture.

## Phase 0 — Prove and freeze the boundary

**Target:** 2026-09-30 through 2026-10-02

### 0.1 Run one official-flow smoke test

On the separate sandbox machine:

1. Install Ubuntu 24.04 x86-64 or an equivalent disposable VM.
2. Create a dedicated non-root user and a CMOS5L-only `PDK_ROOT`.
3. Import the `cmos5l` Tiny Tapeout Verilog template without allowing template
   structure to dictate the internal core architecture.
4. Record immutable revisions for:
   - the template;
   - `tt-gds-action`;
   - `tt-support-tools`;
   - LibreLane;
   - IHP Open PDK;
   - test dependencies.
5. Reconstruct the environment from the GitHub Action rather than trusting the
   currently stale devcontainer defaults.
6. Harden the trivial template design as 1x1.
7. Harden an intentionally trivial 6x4 design.
8. Run precheck and gate-level simulation.
9. Archive build logs, tool versions, cell counts, timing reports, and layout
   images as a reproducible baseline.

Versions observed on 2026-09-30, to be revalidated before pinning:

- GitHub runner: Ubuntu 24.04.
- Python: 3.11.
- PDK name: `ihp-sg13cmos5l`.
- LibreLane action default: `3.1.0.dev3`.
- IHP Open PDK revision used by the action:
  `2bbec755dc67ca3db0261c3d6163e15735d66710`.
- Template branch: `cmos5l`.
- Tiny Tapeout support-tools branch: `ihp-sg13cmos5l`.

Branches are moving references. The plan requires replacing them with exact
commit IDs in our build manifest.

After the second reproducible smoke-test run, stop exercising full
place-and-route during ordinary behavioral work. The environment remains ready
for milestone checks.

### 0.2 Freeze the Tiny Tapeout boundary

Create a deliberately thin `tt_um_*` wrapper around a portable core interface:

```verilog
module mindreader_core (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire [7:0] dedicated_in,
    output wire [7:0] dedicated_out,
    input  wire [7:0] bidir_in,
    output wire [7:0] bidir_out,
    output wire [7:0] bidir_oe
);
```

The neutral names keep the core portable while exposing every Tiny Tapeout
path without prematurely assigning protocol meanings. The wrapper is
responsible only for:

- mapping `ui_in`, `uo_out`, `uio_in`, `uio_out`, and `uio_oe`;
- passing `clk`, `rst_n`, and the Tiny Tapeout enable signal;
- establishing defined safe outputs while disabled or in reset;
- exposing any fixed configuration strap chosen during the pin-budget review.

The wrapper must contain no learner, matcher, protocol decoder, timer, or
response logic.

Write a provisional pin budget covering:

- passive training observation;
- emulation input, output, and output-enable behavior;
- host configuration and trace extraction;
- open-drain operation;
- the physical handoff from real peripheral to emulator.

Freeze only the boundary shape, not final pin meanings. The goal is to ensure
that every architecture we explore can be packaged honestly.

### 0.3 Define the memory boundary

Before learner code grows around an accidental software data structure, define
a small abstract memory interface with two implementations:

- a behavioral Verilog model used by ordinary simulation;
- an IHP SRAM or other physically justified implementation selected only by
  the CMOS5L build.

The core must not instantiate IHP standard cells directly. Vendor-specific
memory wrappers remain below the portable memory interface.

No SRAM macro is selected in Phase 0. We only prevent the architecture from
assuming asynchronous reads, unlimited ports, arbitrary initialization, or
free storage without stating those assumptions.

### 0.4 Establish repository conventions

Create, only as needed:

```text
docs/                 durable specifications and decision records
experiments/          disposable software feasibility work
rtl/                  synthesizable design, after Gate A
sim/                  shared traces and reference-model tests
formal/               properties and formal harnesses
toolchain/            pinned environment and bring-up scripts
reports/              small curated summaries, never raw build trees
```

Generated hardening runs, waveforms, solver dumps, and local PDK files remain
ignored. A report enters Git only when it supports a decision.

### Phase 0 exit criteria

- A clean checkout can produce a valid GDS using exact documented revisions.
- The 6x4 floorplan is accepted by support tools and precheck.
- Gate-level simulation passes for the trivial design.
- A second run is reproducible without repairing the environment manually.
- A trivial portable core is exercised through the real `tt_um_*` wrapper.
- The provisional pin budget proves training and emulation can be connected.
- The core and memory interfaces contain no IHP-specific primitives.
- The existing Sky130 machine and its PDK are never mounted or modified.

## Phase A — Define and test the minimum mindreader

**Target:** 2026-10-01 through 2026-10-13

This phase is software-only. Its purpose is to discover the machine we need,
not to simulate an architecture we already want.

The normal loop in this phase is reference-model tests plus fast RTL simulation
of small candidate primitives. Full Tiny Tapeout hardening is deliberately out
of the loop unless an experiment changes the top-level boundary, clocking
assumption, or memory contract.

### A.1 Write the exact claim

Create `docs/CLAIM-000.md` containing:

- what information the learner is given;
- what it must infer;
- what constitutes a training example;
- what counts as a novel held-out exchange;
- what classes of behavior are representable;
- what the system reports when evidence is insufficient;
- which part must eventually execute on chip;
- an adversarial test that would expose disguised record/replay.

### A.2 Choose the first hypothesis language

Start with a bounded language small enough to imagine in gates:

- a small number of explicit states;
- request predicates expressed as mask/value pairs;
- captured request fields;
- response templates containing constants and captured fields;
- optional copied or inverted request bits;
- quantized response-delay intervals;
- explicit next state;
- an `UNKNOWN` outcome;
- bounded competing alternatives with evidence counts.

Do not begin with arbitrary arithmetic, recursive grammars, unbounded buffers,
or semantic field interpretation.

### A.3 Define a common trace format

Represent observations as edge events rather than protocol-specific packets:

```text
cycle_delta, input_value, input_changed, output_value, output_changed, marker
```

Protocol decoders may annotate this stream, but raw events remain the source of
truth. The same trace fixture must feed the software learner, RTL simulation,
and eventually FPGA tests.

### A.4 Build a graduated trace corpus

Use five levels:

1. **Synthetic combinational peripheral:** response contains constants, copied
   request fields, and one transformed field.
2. **Synthetic stateful peripheral:** identical requests produce different
   responses in different learned states.
3. **Timed peripheral:** correct response data with variable but bounded delay.
4. **Standard framed bus:** UART-, SPI-, or I2C-shaped exchanges while framing
   hints are provided.
5. **Real peripheral or faithful open model:** a sensor, EEPROM, display, or
   similarly legible device with a compact initialization dialogue.

Every corpus is divided before inference into training, held-out valid,
ambiguous, malformed, and unsupported exchanges.

### A.5 Implement the software oracle

The oracle must:

- construct a model incrementally rather than inspect the entire test set;
- distinguish constants from captured or variable fields;
- retain alternative explanations when evidence is ambiguous;
- match and execute its learned model;
- reject unsupported exchanges;
- serialize the model into a hardware-plausible fixed-width form;
- report model bytes, operation counts, maximum alternatives, and response
  latency requirements.

The oracle may use a convenient language and unoptimized data structures for
clarity, but every operation required in the final serialized model must be
enumerated and costed.

### A.6 Demonstrate real generalization

The minimum accepted demonstration is:

1. Train on multiple related request/response pairs.
2. Infer at least one variable relationship rather than storing each pair.
3. Execute a valid request absent from training.
4. Produce the expected response and timing class.
5. Reject a nearby request outside the learned language.
6. Print the model and provenance for the chosen transition.

### Gate A — 2026-10-13: Is the idea real?

Proceed to architecture only if all are true:

- Toolchain Phase 0 has passed.
- The learner succeeds on every held-out case in the deliberately bounded
  flagship family.
- It produces zero false matches on the adversarial unsupported set.
- The result cannot be reproduced by exact trace lookup alone.
- The serialized flagship model is at most 512 bytes.
- Learning can be expressed as bounded streaming updates with no dynamic memory
  allocation, recursion, or unbounded search.
- We can name a meaningful subset of learning that will occur on chip.

If the model generalizes only because a host performs unconstrained inference,
we either reduce the claim explicitly or stop.

## Phase B — Derive the machine from the evidence

**Target:** 2026-10-14 through 2026-11-06

### B.1 Write the model execution specification

Define cycle-accurate behavior for:

- input synchronization and edge capture;
- event timestamping and timer rollover;
- transaction boundaries;
- rule matching and priority;
- simultaneous or ambiguous matches;
- field capture and response substitution;
- atomic output and output-enable changes;
- response scheduling and missed deadlines;
- model update ordering;
- reset, partial models, overflow, and `UNKNOWN`.

This specification, not incidental RTL behavior, becomes authoritative.

### B.2 Finalize the pin plan

Replace the provisional Phase 0 budget with exact assignments. Account
explicitly for:

- eight dedicated inputs;
- eight dedicated outputs;
- eight bidirectional pins and output enables;
- clock and reset;
- training topology between controller and peripheral;
- emulation topology after the peripheral is removed;
- model loading, status, and trace extraction;
- safe open-drain operation for I2C-like buses.

We do not finalize an engine whose flagship demonstration cannot be wired to the
actual Tiny Tapeout interface.

### B.3 Build the smallest hardware kernel

Implement only:

- edge capture;
- deadline/timestamp counter;
- fixed-width rule matcher;
- small explicit state register;
- captured-field registers;
- response template expander;
- atomic pin-value and pin-direction update;
- overflow and unknown indication.

Run manual models for simple UART, SPI, and I2C behavior through the same
kernel. No dedicated fixed protocol blocks count toward this test.

The kernel remains a portable module behind the frozen wrapper. PDK-specific
cells, SRAM macros, and physical-flow workarounds must not leak into its
behavioral contract.

### B.4 Add one meaningful learning primitive

Candidate first primitive:

- accumulate whether each observed response bit is always zero, always one,
  equal to a captured request bit, inverted from one, or unresolved;
- accumulate a bounded response-delay interval;
- promote a stable relation into an executable response template;
- retain `UNKNOWN` when multiple relations still fit.

This is intentionally narrow. It is nevertheless genuine on-chip inference if
the promoted template later answers a held-out request correctly.

### B.5 Verify before optimizing

- Differentially execute every corpus trace in the software model and RTL.
- Assert that unknown rules never drive pins.
- Assert that open-drain configuration never drives a logical high.
- Assert atomicity of output value and direction updates.
- Assert bounded response latency for every accepted transition.
- Cover all rule-selection, timeout, overflow, and ambiguity paths.

### B.6 Return to the physical flow

Once the kernel and first learning primitive are stable:

1. Synthesize the portable core through the real Tiny Tapeout wrapper.
2. Replace behavioral memory with the candidate IHP implementation.
3. Harden the actual 6x4 design.
4. Compare physical timing and memory behavior against the reference model.
5. Record area by block, SRAM geometry, congestion, critical paths, and routing
   margin.

This is the first full hardening run after the smoke test. Its purpose is to
invalidate architectural assumptions early, not to tune a final floorplan.

### Gate B — 2026-11-06: Does the machine fit?

Proceed only if:

- The kernel passes differential and formal tests.
- At least one learning primitive runs in RTL and answers a held-out request.
- UART, SPI, and I2C are expressible without fixed protocol blocks.
- Synthesis uses no more than 60% of the estimated logic budget.
- The selected SRAM organization fits physically with routing access.
- The design meets a 20 ns target clock with positive setup and hold margin.
- A 6x4 place-and-route completes without relying on pathological density.
- The remaining area is credible for control, host interface, and iteration.

If matching or learning dominates the die, revisit the hypothesis language
before micro-optimizing RTL.

## Phase C — Prove the complete story on an FPGA

**Target:** 2026-11-07 through 2026-12-01

### C.1 Select the flagship peripheral

The target should have:

- a short, visible request/response dialogue;
- at least one variable field the learner can generalize;
- at least one state transition;
- modest electrical requirements;
- a controller whose continued operation is obvious to an audience;
- a safe way to remove or switch out the original peripheral.

Candidate categories include a small SPI sensor, I2C EEPROM-like device, or a
display controller with a deliberately constrained command subset. Selection
must follow trace evidence rather than theatrical appeal alone.

### C.2 Demonstrate the loop

On FPGA or equivalent cycle-accurate hardware:

1. Observe controller and peripheral.
2. Build the bounded model using the same learning primitive intended for the
   ASIC.
3. Expose the learned transitions and remaining uncertainty.
4. Disconnect or electrically isolate the peripheral.
5. Answer a request absent from the training set.
6. Keep the controller operating.
7. Present an unsupported request and visibly decline to guess.

### C.3 Stretch: one discriminating experiment

If two candidate relations remain, calculate a request value that would produce
different predicted responses, obtain explicit user approval, query the real
device, and eliminate one candidate.

The first tapeout does not depend on autonomous active probing. Safe passive
learning plus an explainable suggested experiment is sufficient for the core
claim.

### Gate C — 2026-12-01: Is it worth taping out?

Commit to submission only if:

- The full learn/remove/impersonate demonstration works repeatedly.
- A held-out exchange proves generalization.
- Unsupported behavior is handled safely.
- No hidden host inference is required for the demonstrated path.
- FPGA and RTL reference results agree cycle for cycle.
- Current place-and-route still has adequate area, timing, and routing margin.
- The demonstration can be explained honestly in one paragraph.

## Phase D — Harden, prove, and submit

**Target:** 2026-12-02 through 2027-01-18

### D.1 Architecture freeze — 2026-12-08

- Freeze the hypothesis language and serialized model format.
- Freeze the top-level pin mapping and clock assumptions.
- Freeze the learning primitive required for the flagship claim.
- Defer all unrelated accelerators and protocol conveniences.

### D.2 Verification closure — 2026-12-20

- Complete formal safety and deadline properties.
- Run constrained-random traces with malformed timing and pin behavior.
- Perform mutation tests against key properties.
- Run RTL/gate-level differential tests for all curated traces.
- Verify reset, clock interruption, SRAM initialization, and overflow behavior.

### D.3 Physical closure — 2027-01-03

- Complete repeated clean hardening runs.
- Review setup and hold timing at documented corners available in the flow.
- Review utilization, congestion, antenna, DRC, and power-grid results.
- Run post-layout gate-level flagship tests.
- Preserve exact tool and PDK revisions.

### D.4 Submission rehearsal — 2027-01-10

- Build from a clean checkout using the documented environment.
- Run official precheck and gate-level CI.
- Reproduce the FPGA demonstration.
- Complete documentation, diagrams, firmware/models, and verification report.
- Have a technically skeptical reader attempt to disprove the central claim.

### D.5 Buffer and submission — 2027-01-11 through 2027-01-18

No new architecture or features enter during the final week. Only submission
repairs, documentation corrections, and failures of already required tests are
in scope.

## Initial verification matrix

| Property | Software oracle | RTL simulation | Formal | FPGA | Gate-level |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exact replay | Yes | Yes | — | Yes | Yes |
| Held-out generalization | Yes | Yes | Cover | Yes | Yes |
| Unknown request rejected | Yes | Yes | Assert | Yes | Yes |
| Open-drain safety | Model | Yes | Assert | Yes | Yes |
| Atomic pin update | Model | Yes | Assert | Observe | Yes |
| Deadline honored | Yes | Yes | Assert | Measure | Yes |
| Ambiguity retained | Yes | Yes | Cover | Demonstrate | Yes |
| Overflow is safe | Yes | Yes | Assert | Force | Yes |
| Reset from any state | Yes | Yes | Prove | Force | Yes |

## Decision records required

Before Gate B, create short decision records for:

1. `ADR-000`: exact central claim and non-claim.
2. `ADR-001`: trace/event representation.
3. `ADR-002`: hypothesis/model language.
4. `ADR-003`: on-chip versus host learning boundary.
5. `ADR-004`: portable core and Tiny Tapeout wrapper boundary.
6. `ADR-005`: pin topology and training/emulation switching.
7. `ADR-006`: memory technology and allocation.
8. `ADR-007`: implementation language and verification stack.

Each record must include rejected alternatives and the evidence that made the
decision possible.

## Immediate next actions

The first execution slice is deliberately small:

1. Bring up and pin the isolated CMOS5L environment.
2. Produce the trivial 1x1 and 6x4 GDS baselines, then stop using hardening as
   the ordinary development loop.
3. Freeze and test the thin `tt_um_*` wrapper, provisional pin budget, portable
   core interface, and behavioral memory contract.
4. Write `docs/CLAIM-000.md` before learner code.
5. Define the edge-event trace schema and one synthetic peripheral.
6. Build the smallest learner capable of constant/copy/invert field inference.
7. Hold out one request, demonstrate its inferred response, and attack the
   result with unsupported near-neighbor requests.
8. Measure serialized bytes and primitive operations.
9. Conduct Gate A on 2026-10-13.

## Final rule

We are not trying to prove that a sufficiently large computer can infer a
protocol and download an emulator. We are trying to discover a small, honest,
silicon-native learning operation that turns observation into new executable
behavior.

If we cannot show that operation clearly, we do not have the project yet.
