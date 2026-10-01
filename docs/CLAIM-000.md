# CLAIM-000: Minimum Falsifiable Mindreader

**Status:** active experiment  
**Date:** 2026-09-30  
**Decision gate:** prove generalization before choosing the RTL architecture

## Claim

Given several timed request/response examples from a peripheral in a bounded
protocol class, Protocol Doppelganger can infer an executable model that:

1. recognizes the demonstrated request family;
2. constructs responses from constants and fields copied from the request;
3. reproduces the demonstrated response latency;
4. answers at least one valid request not seen during training; and
5. returns `UNKNOWN` when the evidence does not determine a unique model.

This is a deliberately small claim. It is stronger than waveform replay but
does not yet claim framing discovery, multiple states, active probing, or
arbitrary protocol inference.

## Information given to the learner

Experiment 000 gives the learner a set of transactions. Each transaction has:

- one 8-bit request;
- one 8-bit response; and
- the integer number of cycles between request completion and response start.

Transaction boundaries and byte alignment are supplied. Later experiments
must remove those conveniences and learn from edge-timed pin traces.

Experiment 001 first supplies the same boundaries as annotations on the raw
cycle-delta edge stream defined by `TRACE-000.md`, then removes every marker
and recovers the boundaries from observable select, clock, and response-valid
edges. A fixture-specific decoder samples the synthetic serial link and
reconstructs the transactions. The learner itself remains unchanged.

## Hypothesis language

The first learner may represent:

- a single state;
- one request predicate expressed as an 8-bit mask and value;
- each response bit as constant zero, constant one, a copied request bit, or an
  inverted request bit;
- one exact response delay; and
- an explicit `UNKNOWN` result.

Only request bits that vary in the evidence may be used as response fields.
Bits that remain stable become the provisional request-family predicate. This
rule prevents a constant command bit from masquerading as a learned field, but
it also means the initial learner can over-specialize when the corpus lacks
variation. That limitation is intentional and testable.

## Experiment 000

The synthetic peripheral accepts requests `0xA0` through `0xAF`. After six
cycles it returns `0x60 | request[3:0]`.

Training requests vary every payload bit but exclude `0xA7`. The held-out test
requires the learner to produce `0x67` after six cycles for `0xA7`.

Controls:

- an exact replay table must fail on `0xA7`;
- the learned model must reject `0xB7`;
- a deliberately underdetermined training set must remain incomplete and
  return `UNKNOWN`;
- inconsistent observed delays must remain unresolved rather than being
  averaged or silently selected.

The experiment passes only if all four controls and the held-out test pass.

## Why this demonstrates generalization

`0xA7` is absent from the training set, so a request-indexed replay table has no
answer. Producing `0x67` requires combining a learned request-family predicate,
four independently inferred request-to-response bit relationships, four
constant response bits, and a learned delay.

This is still a controlled form of generalization. It proves the first useful
step, not the overall project.

## Execution plan

1. **Transaction learner — implemented.** The initial hypothesis language,
   replay baseline, synthetic peripheral, held-out test, and ambiguity tests
   pass locally and are included in the fast CI workflow.
2. **Edge trace format — implemented.** Cycle-delta pin events, canonical
   validation, CSV round trips, and a serial synthetic-link codec recover the
   Experiment 000 corpus and preserve its held-out result.
3. **Bounded framing and timing — implemented for the synthetic link.** With
   all markers removed, select and response-valid edges delimit phases, clock
   edges recover both bytes, and observable edge timing recovers latency. Pin
   roles, active levels, sampling edge, byte width, and bit order remain given.
4. **Bounded state — implemented for a two-state toggle hypothesis.** Reset-
   delimited sequences identify a unique control request, learn independent
   response templates in both inferred states, and generalize an unseen
   payload across the transition. See `STATE-000.md`.
5. **Active disambiguation — implemented for bounded response templates.**
   Sparse evidence expands to every consistent model, deterministic probe
   selection minimizes the worst-case survivor set, and observations prune the
   set to one model or an explicit contradiction. See `ACTIVE-000.md`.
6. **Hardware extraction — started.** `HARDWARE-000.md` derives a compact
   streaming candidate-mask learner from Experiments 000–003. The first
   synthesizable kernel updates request predicates, response uncertainty, and
   exact timing without enumerating complete models. A paired executor now
   recognizes and answers the held-out request at the learned cycle, closing
   the first RTL learn-to-emulate loop.
7. **Executable protocol program — implemented at the behavioral layer.**
   Complete stateless and two-state learned models compile into the same
   validated ten-byte transition format. Binary round trips preserve held-out
   behavior, overlapping guards are rejected, and unknown requests cannot
   change state. See `GRAMMAR-000.md`.
8. **Physical convention search — implemented for sampling edge and bit
   order.** Markerless traces uniquely determine rising versus falling-edge
   sampling when data changes on the opposite edge. Bit order remains a
   two-member equivalence class because consistent bit reversal preserves all
   observed behavior; the learner retains that uncertainty. See
   `PHYSICAL-000.md`.
9. **Pin-role search — implemented with fixed direction and width.** The
   learner evaluates 48 assignments spanning input roles, output roles,
   sampling edge, and bit order. Default and permuted fixtures uniquely recover
   every role and the sampling edge; only the known bit-reversal symmetry
   remains. See `PHYSICAL-000.md`.
10. **Width inference — implemented with fixed framing boundaries.** Eight-
    and six-bit fixtures recover their exact request/response phase widths.
    Every divisor remains an equivalent symbol granularity, separating
    observable bit count from unobservable word naming. See `WIDTH-000.md`.
11. **Variable framing — implemented for length and delimiter hypotheses.**
    Learned rules segment boundary-free held-out streams; ambiguous training
    retains both explanations until additional evidence distinguishes them.
    See `FRAMING-000.md`.
12. **Integrity inference — implemented for a bounded one-byte catalog.**
    Constant, XOR, two additive rules, and four named CRC-8 configurations
    compete against held-out frames. Ambiguous rules produce a distinguishing
    payload probe rather than an arbitrary winner. See `INTEGRITY-000.md`.
13. **Known-protocol benchmark — first tranche implemented.** Thirteen golden
    anonymous-pin waveforms cover SPI modes 0–3 in both bit orders, four UART
    8N1 values, and one acknowledged I²C write. Reference decoders pass; the
    learner has not yet been scored against them. See `CORPUS-000.md`.
14. **Known-corpus capture score — implemented.** Every waveform round-trips
    through the anonymous delta-edge representation and yields a pin activity
    profile. All 13 cases then fail the current selected-serial frontend for
    documented topology reasons, establishing an honest baseline rather than
    retrofitting the benchmark. See `CORPUS-000.md`.
15. **Canonical SPI frontend — implemented.** A 384-hypothesis anonymous-pin
    search advances every SPI mode/order fixture through topology and symbol
    extraction. Physical timing is unique; data direction and bit order remain
    explicit two-way symmetries. See `SPI-000.md`.
16. **Joint SPI behavior — implemented.** Eight transfers sharing unknown
    physical conventions resolve data direction when the response relation is
    lossy, retain it when the relation is reversible, generalize to an unseen
    transfer, and compile to a 10-byte program. See `SPI-001.md`.
17. **Hierarchical learned artifact — implemented.** Resolved SPI topology,
    one canonical behavioral program, bit-reversal equivalence, and compact
    provenance serialize to 22 bytes and round-trip without changing held-out
    wire behavior. Unresolved causal direction is rejected. See `MODEL-000.md`.
18. **Model provenance — implemented as an optional sidecar.** Evidence
    fingerprints and support masks distinguish supported claims, harmless
    equivalence, and unresolved causal direction. Reversible SPI requests drive
    ownership evidence instead of a meaningless value probe. See
    `PROVENANCE-000.md`.
19. **Serialized-model RTL execution — implemented at the word boundary.**
    Synthesizable RTL atomically validates the exact 22-byte hierarchical
    artifact, exposes its learned physical fields, executes its packed
    transition on a held-out request, and rejects both malformed models and
    out-of-family traffic. The boundary also makes pin-level response causality
    an explicit next hypothesis rather than an accidental assumption. See
    `RTL-MODEL-000.md`.
20. **SPI response causality — implemented for the expression language.**
    Each response dependency is placed on the wire-time axis and classified as
    precomputable, prefix-causal, same-symbol causal, or noncausal. The learned
    corpus is same-symbol causal across all modes and fixture orders, exposing
    a launch-to-sample timing measurement as the next required evidence. See
    `CAUSALITY-000.md`.
21. **Wire-facing SPI impersonation — implemented for stream-causal models.**
    RTL loads the learned artifact, remaps anonymous physical roles, follows the
    inferred clock convention, and emits a held-out response bit by bit. It
    releases the response pin on deselect and refuses to drive a well-formed
    but noncausal program. See `SPI-RTL-000.md`.
22. **Passive authority and trace capture — implemented.** A fail-safe
    supervisor separates observation, candidacy, admission, emulation, and
    fault, with combinational drive revocation. A bounded anonymous-edge FIFO
    makes trace loss sticky and invalidates incomplete evidence. See
    `SUPERVISOR-000.md`.
23. **Passive SPI physical inference in RTL — implemented.** Hardware evaluates
    all ordered select/clock assignments from anonymous pin transitions and
    recovers roles, polarity, idle level, and sampling edge across all modes,
    orders, and a permuted fixture. Data direction remains explicitly
    unresolved. See `SPI-RTL-LEARN-000.md`.
24. **Autonomous SPI learn-to-impersonate loop — implemented.** Inferred
    topology decodes wire traffic into two competing causal directions; only a
    unique, causal, timing-safe, ownership-authorized model can be frozen. The
    resulting RTL answers an unseen wire request without host-generated model
    bytes and remains high-impedance throughout learning. See
    `AUTONOMOUS-000.md`.
25. **Request-guard causality — implemented.** Guard bits and response bits are
    placed on the same wire-time axis. The MSB corpus has a constant speculative
    prefix; canonical LSB models expose input-dependent output before their
    request family is known. See `GUARD-000.md`.
26. **SPI boundary safety — implemented.** Exact-length acceptance rejects
    truncated and overlong frames, measured edge intervals gate timing safety,
    and pad-loopback disagreement removes drive permission immediately and
    latches contention. See `SPI-SAFETY-000.md`.
27. **Mindreader control kernels — implemented.** Hardware proposes a
    distinguishing request but transmits only after authorization, executes a
    bounded multi-state program without unknown-request state mutation, and
    exposes evidence, survivors, uncertainty, admission, and fault status. See
    `MINDREADER-CONTROL-000.md`.
28. **UART and I²C frontends — implemented at the inference boundary.**
    Anonymous UART traces retain polarity, period, width, parity, and stop-bit
    equivalence while rejecting a malformed canonical frame. Anonymous I²C
    traces recover clock/data roles, bytes, ACK ownership, and repeated-start
    frame boundaries while recording the open-drain execution constraint. See
    `SERIAL-FRONTENDS-000.md`.
29. **Adversarial corpus and honest benchmark — implemented.** Six invented
    protocols exercise variable width, competing framing rules, integrity,
    state, ambiguity, corruption, and noncausal behavior. A generated 19-case
    report records how far each known and invented case progresses, the
    evidence and equivalence remaining, held-out behavior, replay failure,
    refusal, and unsupported claims. See `ADVERSARIAL-000.md` and
    `BENCHMARK-000.md`.

Each step must retain the replay control, an unseen valid exchange, an unknown
request, and an insufficient-evidence case. A step does not pass merely because
its demonstrations look plausible.

## Stop or narrow conditions

Reconsider the architecture or claim if:

- generalization requires host-only computation that cannot be bounded for the
  target;
- ambiguity cannot be represented compactly;
- the useful model cannot be stored or searched within the 6x4 budget;
- response scheduling cannot meet inferred deadlines; or
- later trace-level experiments succeed only because protocol-specific facts
  were hidden in the test harness.
