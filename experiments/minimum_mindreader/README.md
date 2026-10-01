# Minimum Mindreader Experiment

This directory implements Experiments 000 and 001 from `docs/CLAIM-000.md`.
The learner still consumes bounded transactions, but Experiment 001 obtains
those transactions by decoding the protocol-neutral edge records specified in
`docs/TRACE-000.md`.

The Experiment 001 regression covers both an annotated codec and a markerless
path. The markerless path removes all annotations, detects the transaction from
select, clock, and response-valid edges, recovers the response delay, and then
feeds the unchanged learner. The fixture still supplies pin roles, clock edge,
byte width, and bit order; inferring those remains future work.

Run the demonstration:

```sh
python3 experiments/minimum_mindreader/run_experiment.py
python3 experiments/minimum_mindreader/run_state_experiment.py
python3 experiments/minimum_mindreader/run_active_experiment.py
python3 experiments/minimum_mindreader/run_protocol_program.py
python3 experiments/minimum_mindreader/run_framing_experiment.py
python3 experiments/minimum_mindreader/run_role_experiment.py
python3 experiments/minimum_mindreader/run_width_experiment.py
python3 experiments/minimum_mindreader/run_variable_framing.py
python3 experiments/minimum_mindreader/run_integrity_experiment.py
python3 experiments/minimum_mindreader/run_known_corpus.py
python3 experiments/minimum_mindreader/run_corpus_score.py
python3 experiments/minimum_mindreader/run_spi_experiment.py
python3 experiments/minimum_mindreader/run_spi_behavior.py
python3 experiments/minimum_mindreader/run_hierarchical_model.py
python3 experiments/minimum_mindreader/run_model_provenance.py
python3 experiments/minimum_mindreader/run_spi_causality.py
```

Run the tests:

```sh
python3 -m unittest discover -s experiments/minimum_mindreader -p 'test_*.py'
```

The implementation uses only the Python standard library. It is an oracle for
exploring the trace and model languages, not production host software and not
an RTL architecture.

Experiment 002 adds a bounded two-state hypothesis. From reset-delimited
sequences it identifies the unique request that toggles hidden state, learns a
separate response template in each state, and answers an unseen payload before
and after the inferred transition. See `docs/STATE-000.md` for its precise
scope and non-claims.

Experiment 003 begins with sparse evidence that admits 256 response templates.
It proposes requests that minimize the worst-case surviving candidate set,
updates from the observed timed response, and stops only when one executable
model remains. See `docs/ACTIVE-000.md`.

The first behavioral protocol-program experiment compiles both the stateless
and two-state learned models into the same validated fixed-record format. It
measures 10 bytes for the stateless program and 40 bytes for the toggle program,
then verifies serialization and held-out behavior. See `docs/GRAMMAR-000.md`.

The physical convention experiment enumerates rising/falling sampling and
MSB/LSB-first decoding over markerless traces. It recovers the configured
sampling edge while retaining bit order as an explicit observational symmetry.
See `docs/PHYSICAL-000.md`.

The pin-role extension evaluates all 48 assignments of three input roles, two
output roles, sampling edge, and bit order. It recovers both default and
permuted wiring from corpus-wide behavioral consistency, again retaining only
the two equivalent bit-order interpretations.

The width experiment observes exact request and response bit counts from the
framed phases, then retains every divisor as a compatible symbol granularity.
It covers both eight-bit and six-bit fixtures to avoid baking byte assumptions
into the protocol grammar. See `docs/WIDTH-000.md`.

The variable-framing experiment learns either a bounded length-field rule or
an unescaped terminal delimiter, then segments held-out streams without frame
boundaries. A controlled ambiguous corpus retains both models until one more
frame distinguishes them. See `docs/FRAMING-000.md`.

The integrity experiment compares a constant negative control, XOR, additive
checksums, and four named CRC-8 configurations. It validates held-out corruption
and proposes a distinguishing payload when multiple rules fit. See
`docs/INTEGRITY-000.md`.

The known-protocol corpus begins with 13 golden waveforms covering SPI, UART,
and I²C. Inference receives anonymous indexed-pin samples; protocol labels,
roles, and expected symbols remain scorer-only. Each family now reaches its
bounded inference frontend. See `docs/CORPUS-000.md`.

The corpus scorer losslessly converts every golden waveform to anonymous edge
events and profiles each pin. Its original failure matrix documented why all
three families violated the synthetic selected-serial frontend; the evolving
scorer now reaches `spi_symbols`, `uart_symbols`, and `i2c_frames`.

The SPI frontend evaluates 384 anonymous four-pin hypotheses. All eight
canonical SPI cases uniquely recover select polarity, clock idle level, and
sampling edge, while retaining data-direction and bit-order symmetries. The
corpus scorer now advances SPI through `spi_symbols`. See `docs/SPI-000.md`.

The joint SPI behavior experiment applies the physical hypotheses across eight
transfers. A lossy request/response relation resolves data direction, retains
only bit-order equivalence, generalizes to an unseen request, and compiles to a
10-byte protocol program. A reversible control correctly preserves direction
ambiguity. See `docs/SPI-001.md`.

The hierarchical-model experiment canonicalizes the remaining bit-order pair
into one physical descriptor, one 10-byte behavioral program, an equivalence
flag, and compact evidence counts. The complete artifact is 22 bytes and
round-trips without changing held-out wire behavior. See `docs/MODEL-000.md`.

The provenance experiment adds a 56-byte optional sidecar containing waveform
fingerprints, per-claim support sets, distinct equivalent/unresolved statuses,
and a typed missing-evidence request. The 22-byte real-time model remains
unchanged. See `docs/PROVENANCE-000.md`.

The first serialized-model RTL boundary loads that exact 22-byte core,
validates it atomically, exposes its learned physical fields, and executes its
packed transition on a held-out request. See `docs/RTL-MODEL-000.md`.

The SPI causality analyzer maps request/response expression dependencies onto
wire time. It proves the current learned relation needs no future request bit,
while naming the launch-to-sample margin that a pin-level executor must still
meet. See `docs/CAUSALITY-000.md`.

The wire-facing SPI RTL loads the same artifact, uses its learned anonymous-pin
map and clock convention, and emits the held-out `0x63` response under an
external mode-1 clock. A causal admission gate prevents future-bit programs
from enabling the response driver. See `docs/SPI-RTL-000.md`.

The passive-authority RTL adds the missing operational boundary: reset and
learning are high-impedance, admitted models still require explicit ownership,
and contention latches a fault. Its companion edge FIFO records anonymous pin
changes and poisons evidence on overflow. See `docs/SUPERVISOR-000.md`.

The passive SPI physical learner evaluates every ordered select/clock pairing
directly in RTL. Across all modes, both corpus orders, and permuted pins it
recovers physical timing while retaining the unordered data pair. See
`docs/SPI-RTL-LEARN-000.md`.

The autonomous RTL proof chains physical inference, anonymous transaction
decoding, dual-direction behavioral learning, guarded model promotion, the
passive supervisor, and wire execution. It learns from eight observed frames
and answers an unseen ninth request without any host-produced model bytes. See
`docs/AUTONOMOUS-000.md`.

The guard-causality analysis determines when a request is known to belong to a
learned family and which earlier response bits were necessarily speculative.
It separates constant prefixes from request-dependent speculation. See
`docs/GUARD-000.md`.

The SPI safety boundary accepts only exact-length frames, measures observed
edge timing against configured margins, and latches pad-loopback contention
while removing drive permission immediately. See `docs/SPI-SAFETY-000.md`.

The control-plane kernels add authorized distinguishing probes, a four-record
stateful executor, and an indexed status surface for evidence, survivors,
uncertainty, admission, and faults. See `docs/MINDREADER-CONTROL-000.md`.

Anonymous UART and I²C frontends now infer compatible framing parameters and
pin roles without receiving protocol labels. See `docs/SERIAL-FRONTENDS-000.md`.

The adversarial corpus exercises variable width, competing framing grammars,
integrity and corruption, state, ambiguity, and impossible response causality.
The generated benchmark scorecard reports successes, equivalences, refusals,
replay failures, and unsupported claims for every case. See
`docs/BENCHMARK-000.md`.

The wire-execution matrix now covers all four SPI modes, both corpus wire
orders, and a fully permuted pin map using the same serialized model executor.
