# Protocol Doppelganger

> A self-programming protocol emulator that learns the timed behavior of a
> digital peripheral, explains what it knows, and can impersonate the original
> device.

**Status:** autonomous SPI tapeout candidate, passive polyglot frontend, and
bounded adaptive open-drain interrogation integrated. The earlier polyglot
revision completed the CMOS5L backend; the newer knowledge and interrogation
logic requires a final backend rerun.

This is a prospective entry for Jane Street's
[Protocol Emulator ASIC Competition](https://blog.janestreet.com/protocol-emulator-asic-competition/).
The competition asks for an open-source, general-purpose protocol emulator in a
6x4 Tiny Tapeout allocation targeting IHP's 130 nm CMOS5L process.

The obvious solution is a small processor with instructions for reading pins,
writing pins, and waiting an exact number of cycles. That would be useful, but
it would also be one of many smaller variations on RP2040 PIO or TI PRU.

Protocol Doppelganger starts from a different question:

> Can the emulator discover enough of a device's protocol to program itself?

## The idea

Connect Doppelganger to a controller and a peripheral during a training phase.
It observes their exchanges, discovers timing and framing, and builds a compact
model of the conversation. Remove the original peripheral and switch modes;
Doppelganger answers the controller in its place.

The intended experience is:

1. **Observe** a real device operating normally.
2. **Infer** transaction boundaries, stable and variable fields, timing
   constraints, and request/response state transitions.
3. **Explore** ambiguities by proposing or issuing carefully bounded queries to
   the original device.
4. **Emulate** the learned behavior with deterministic cycle-level timing.
5. **Explain** which behavior was observed, generalized, or remains unknown.

The implementation taxonomy is structural rather than brand-based: shared pin
evidence routes concurrently toward asynchronous single-wire, selected
synchronous, and shared two-wire hypotheses. See
[`docs/TAXONOMY-STATUS-001.md`](docs/TAXONOMY-STATUS-001.md). The integrated
UART candidate bank retains pin, polarity, period, width, parity, and stop-bit
equivalence without driving; see
[`docs/UART-RTL-001.md`](docs/UART-RTL-001.md).
The shared-two-wire bank updates directed clock/data candidates on every edge
and recognizes byte/ACK framing; see
[`docs/I2C-RTL-001.md`](docs/I2C-RTL-001.md).
Protocol-neutral framing simultaneously retains two-edge control, quiet-gap,
and repeated-event-count explanations; see
[`docs/GENERIC-FRAMING-RTL-001.md`](docs/GENERIC-FRAMING-RTL-001.md).
An equivalence classifier merges all ready inference surfaces into structural
survivors and reports unique, equivalent, or insufficient without choosing a
protocol brand; see
[`docs/EQUIVALENCE-RTL-001.md`](docs/EQUIVALENCE-RTL-001.md).

The integrated knowledge report turns those survivors into a useful answer:
what is known, whether the observation was trustworthy, which candidate
boundaries were actually observed, why inference stopped, what evidence to
seek next, and whether active behavior is electrically and explicitly
authorized. See
[`docs/KNOWLEDGE-RTL-001.md`](docs/KNOWLEDGE-RTL-001.md). Its recommendations
are advisory and cannot assert a protocol-pin output enable.

Active interrogation is intentionally isolated from test truth. A black-box
target hides one of several invented open-drain behaviors; the synthesizable
learner derives candidates from the integrated passive shared-two-wire
frontend, chooses requests that divide them, and revises the candidate set from
wire-level ACK/NACK evidence. Explicit ownership and a fresh activation edge
authorize one low-or-release probe. The same closed loop now passes through the
TinyTapeout top without receiving the hidden selection. See
[`docs/INTERROGATION-SIM-001.md`](docs/INTERROGATION-SIM-001.md) and
[`docs/INTERROGATION-INTEGRATION-001.md`](docs/INTERROGATION-INTEGRATION-001.md).

This is not an attempt to recover human meaning such as "this byte is
temperature." It is an attempt to learn an executable, timed behavioral model.

## Flagship demonstration

A controller repeatedly communicates with an unfamiliar sensor or display.
Doppelganger watches several interactions and produces a model. The peripheral
is then physically disconnected.

The controller continues operating against Doppelganger, including at least one
request sequence that did not appear verbatim during training.

The demonstration must show real generalization. Replaying a captured waveform
is a useful fallback feature, but it is not the central claim.

The strongest version of the demo also introduces an ambiguity during passive
training. Doppelganger identifies the ambiguity, selects an experiment that
distinguishes the candidate models, observes the real peripheral's response,
and updates its model before taking the peripheral's place.

## What "learn the protocol" means

Protocol discovery has several layers. We intend to be precise about which
ones the device can and cannot perform.

| Layer | Example questions | Goal |
| --- | --- | --- |
| Electrical structure | Which lines act like clock, data, select, or open-drain signals? | Infer where evidence is sufficient; otherwise accept hints. |
| Timing and framing | What are the symbol period, active edge, idle state, and transaction boundaries? | Infer automatically. |
| Conversation grammar | Which request patterns cause which responses and state changes? | Learn a bounded timed state machine. |
| Semantics | Does a field represent temperature, an address, or a reset command? | Explicitly out of scope. |

No finite observation can determine arbitrary unseen behavior. Doppelganger
must therefore represent uncertainty rather than fabricate certainty. Unknown
inputs, conflicting examples, and underdetermined transitions are first-class
results.

## Learned model

The working abstraction is a **timed Mealy machine** with masked fields and
response templates.

```text
state IDLE:
    request 1010_????  -> emit 0110_$0 after 6 cycles -> READY
    request 1111_0000  -> emit 0000_0001 after 4 cycles -> IDLE
    otherwise          -> UNKNOWN

state READY:
    request 00xx_xxxx  -> emit SAMPLE[7:0] within [4, 6] cycles -> IDLE
```

Transitions may include:

- a predicate over observed pins or decoded symbols;
- captured fields reused in a response;
- a next state;
- minimum, nominal, and maximum response timing;
- an output waveform or response template;
- confidence and provenance information;
- alternatives that require another experiment to distinguish.

The stored representation will probably be closer to a compressed prefix
graph than a textbook state-machine table. The exact choice must be driven by
SRAM cost and streaming lookup latency.

## Protocol grammar

The familiar lifecycle—quiet, synchronization, metadata, payload, integrity,
and termination—is treated as a set of optional semantic roles, not six
mandatory hardware states. Protocols are expected to be small programs built
from recurring physical, framing, field, and behavioral operations.

The first evidence-backed behavioral representation is implemented now. A
guarded transition stores current and next state, a masked request predicate,
eight response expressions, and exact timing in ten bytes. The learned
stateless example occupies 10 bytes; the learned two-state example occupies 40
bytes and runs on the same interpreter. See `docs/GRAMMAR-000.md`.

## Operating modes

### Learn

Capture pin changes with cycle-relative timestamps, segment them into candidate
transactions, and accumulate examples. Repeated observations reveal stable
bits, variable fields, and likely causal request/response pairs.

### Emulate

Match incoming activity against the learned machine and generate the selected
response with deterministic timing. Unsupported or ambiguous requests follow a
configured policy: remain silent, flag the host, replay a default, or enter
exploration mode.

### Explore

When multiple models fit the evidence, choose a low-risk query whose possible
responses divide the candidates. Initially, active probes may require host
approval; autonomous probing is a stretch goal.

### Trace and replay

Record delta-timed pin transitions in a compact format and reproduce them
exactly. Captured fields can be replaced with parameters or mutations. This
makes the chip useful even when inference fails and enables deterministic fault
injection.

### Manual

Run a hand-authored model or microprogram. UART, SPI, and I2C should work in this
mode regardless of how much autonomous learning is ultimately feasible. This
is both the conventional protocol-emulator baseline and the escape hatch for
behaviors that cannot be inferred safely.

## Architectural direction

Doppelganger should not be a conventional general-purpose CPU. Its native
operation should be a guarded, timed, atomic transition:

```text
wait until <pin predicate> or <deadline>
sample selected inputs
update compact state
atomically change output values and output enables
optionally append a trace event
```

A possible high-level organization is:

```text
                    +----------------------+
external pins ----> | synchronizers / edge | ----+
                    | capture              |     |
                    +----------------------+     v
                                               +------------------+
host/configuration <--> SRAM <---------------> | timed transition |
                         ^                     | engine           |
                         |                     +------------------+
                         |                       |       |
                    +----------+                 |       v
                    | learner  | <---------------+   pin drivers
                    | support  | ---- model updates / uncertainty
                    +----------+
```

The silicon budget argues for one small execution datapath with one or two
lightweight contexts, rather than many duplicated processors. Candidate
hardware primitives include:

- input edge detection and pin predicates;
- an exact deadline timer;
- atomic masked updates to output and output-enable registers;
- compact shift, compare, and field-capture operations;
- delta-time trace encoding;
- streaming prefix/model lookup;
- optional CRC support if synthesis proves it earns its area;
- safe open-drain behavior and explicit contention checks.

Program storage and learned traces may share SRAM dynamically. We should assume
memory, not arithmetic, is the limiting resource until synthesis proves
otherwise.

## Where inference runs

There are three possible partitions:

1. **Capture on chip; infer on a host; emulate on chip.** Lowest risk, but the
   silicon itself is not genuinely self-programming.
2. **Frame and build a bounded model on chip; inspect and refine on a host.**
   Current preferred direction.
3. **Perform the entire learning loop on chip.** Best headline, highest risk,
   and likely unrealistic within the target memory budget.

The project remains interesting only if the fabricated design performs a
meaningful inference step. Host software may visualize, label, merge, or verify
models, but it should not secretly do all of the discovery.

One plausible boundary is:

- hardware discovers edge timing, candidate frames, repeated patterns, masked
  fields, and a bounded request/response trie;
- host software performs expensive state merging and suggests active probes;
- hardware validates and executes the resulting model;
- a deliberately small model can be learned and deployed without a host.

## Verification as part of the design

The verification story should be as distinctive as the architecture.

The model compiler should emit not just executable data but a checkable timing
contract:

- maximum response latency for every supported transition;
- proof that conflicting contexts cannot drive the same pin;
- proof that open-drain outputs never actively drive high;
- bounds checks for every captured or substituted field;
- explicit behavior for deadlines and unknown inputs;
- generated assertions for protocol-specific invariants.

The planned verification stack is:

- an executable reference model independent of the RTL;
- differential tests between the reference model, RTL simulation, and compiled
  models;
- property-based generation of traces and candidate state machines;
- formal checks of the transition engine and pin-safety invariants;
- mutation testing to demonstrate that the properties detect real defects;
- post-synthesis and post-layout replay of the flagship traces;
- FPGA testing against physical peripherals before submission.

Human-readable timing diagrams should be executable test fixtures. A protocol
example in the documentation should be the same artifact used to test the
implementation.

The known-protocol benchmark begins with 13 anonymous-pin waveforms spanning
all four SPI modes in both bit orders, UART 8N1, and an acknowledged I²C write.
Protocol labels and pin roles are scorer-only truth, never learner input. See
`docs/CORPUS-000.md`.

## Success criteria

The project is successful if the following can be demonstrated within the ASIC
constraints:

- UART, SPI, and I2C can be implemented manually on the same general engine.
- The chip autonomously infers framing or timing for at least two substantially
  different protocol families.
- The chip constructs a usable request/response model from multiple examples.
- The learned model handles at least one valid exchange not captured verbatim.
- Unknown behavior is reported as unknown rather than matched accidentally.
- The original peripheral can be removed and impersonated in a live demo.
- At least one nontrivial safety or timing claim is formally verified.
- The design completes the full ASIC flow with credible area and timing margin.

## Non-goals

- Understanding the human meaning of arbitrary fields.
- Inferring every behavior of an unrestricted black box.
- Replacing a high-bandwidth logic analyzer.
- Implementing a large general-purpose processor.
- Winning through a long checklist of fixed protocol blocks.
- Using "AI" as a substitute for a falsifiable technical claim.

## Principal risks

### The learner becomes record/replay with ambitious branding

This is the central product risk. The flagship test must include generalization
to an exchange not observed verbatim.

### Inference does not fit

Roughly 1 KiB-class SRAM and a roughly 24K-cell budget leave little space for
general algorithms. We must prototype the model representation and synthesize
it before investing in a large toolchain.

### Too much magic, too few guarantees

Automatic pin-role and framing inference will fail on ambiguous traces. Hints
and explicit uncertainty are acceptable; silent guesses are not.

### Active exploration can damage or confuse a target

Probes need electrical and logical safety policies. Early versions should
require host approval and enforce strict pin-direction and rate constraints.

### The host does everything interesting

The boundary between hardware and software must be visible in the demo and
documentation. At least one meaningful learning path must run autonomously in
silicon.

### Physical I/O dominates the architecture

Training between two endpoints, later impersonating one endpoint, and loading
models all compete for a small number of pins. Pin topology and mode switching
must be settled before the instruction set.

## Go / no-go experiments

No RTL architecture should be committed until these questions have concrete
answers.

1. **Trace corpus:** Capture representative UART, SPI, and I2C peripheral
   sessions, including stateful and variable responses.
2. **Software oracle:** Demonstrate that a deliberately small learner can infer
   a timed masked model and generalize beyond exact replay.
3. **Representation:** Measure the memory required for those models after
   compression.
4. **Cycle model:** Show that matching and response scheduling meet the hardest
   intended deadlines at a realistic Tiny Tapeout clock.
5. **Hardware kernel:** Synthesize the minimal capture, matcher, timer, and pin
   update datapath against the target cell library.
6. **I/O plan:** Prove that training, configuration, and emulation are usable
   with the available dedicated and bidirectional pins.
7. **Killer demo rehearsal:** Perform the complete learn, disconnect, and
   impersonate sequence in software or on an FPGA.

Proceed only if the learner generalizes, the model fits comfortably, and the
hardware kernel leaves substantial area and timing margin. Otherwise, reduce
the claim honestly to a timed protocol laboratory—or do not submit.

## Tentative milestones

### Phase 0: Decide whether the idea is real

- Define the inference claim precisely.
- Build the trace corpus and software learner.
- Rehearse the flagship demo without custom hardware.
- Establish memory, pin, area, and clock budgets.

### Phase 1: Prove the hardware primitive

- Implement the timed transition engine.
- Implement capture and exact replay.
- Run UART, SPI, and I2C as manual programs.
- Establish formal pin-safety and deadline properties.
- Synthesize early and run an initial place-and-route.

### Phase 2: Put learning in the loop

- Add streaming segmentation and pattern accumulation.
- Build and update a bounded model on chip.
- Expose uncertainty and model provenance to the host.
- Demonstrate novel-exchange generalization on an FPGA.

### Phase 3: Make it undeniable

- Complete the live peripheral substitution demo.
- Add one safe active-learning experiment.
- Freeze the architecture and harden the ASIC.
- Publish the compiler, model viewer, proofs, traces, and reproducible results.

## Open questions

- What is the smallest inference result that unquestionably counts as learning?
- Must training be passive, inline, or switchable between both?
- Can a single compact representation support learning, execution, and trace
  replay?
- How much autonomy must live in silicon for the central claim to feel honest?
- Which physical peripheral makes the clearest and most surprising demo?
- What happens on a partially matched or entirely novel request?
- Can active queries be made electrically safe without consuming too much area?
- Is one execution context sufficient, or does full-duplex behavior require two?
- Does the foundry SRAM macro support the access pattern and capacity we need?

## One-sentence test

If the finished project cannot truthfully make this claim, it has lost its
reason to exist:

> Doppelganger watched a device, learned a timed behavioral model, and replaced
> it successfully—including behavior that was not captured as an exact replay.
