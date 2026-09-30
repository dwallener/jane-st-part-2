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
