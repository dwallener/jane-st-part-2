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
roles, and expected symbols remain scorer-only. The current gate validates the
reference fixtures, not learner success. See `docs/CORPUS-000.md`.

The corpus scorer losslessly converts every golden waveform to anonymous edge
events and profiles each pin. Its initial failure matrix deliberately stops all
13 cases before the current selected-serial frontend, documenting why SPI,
UART, and I²C each violate that frontend's topology assumptions.
