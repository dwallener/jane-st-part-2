# INTERROGATION-SIM-001: Chinese-Wall Closed-Loop Simulation

**Status:** first randomized open-drain kernel implemented; corpus-wide harness open
**Date:** 2026-10-01

## Goal

Demonstrate interrogation without allowing test truth to leak into Mindreader.
The eventual benchmark chooses a random canonical or invented protocol from the
test suite, supplies only anonymous traffic and electrically permitted actions,
and scores whether Mindreader resolves uncertainty or refuses safely.

“Success” does not require every protocol to be actively probed. A one-way UART
or a protocol with no established safe query can correctly produce
`NO_ADMISSIBLE_PROBE`. Guessing or driving anyway is failure.

## Chinese Wall

The simulation is divided into four roles:

1. **Scenario vault:** randomly chooses the secret target and owns golden truth.
2. **Behavioral host and target:** convert that truth into ordinary pin traffic
   and responses. They never write inference state or DUT configuration.
3. **Mindreader DUT:** receives sampled pins, candidate state derived from
   public evidence, electrical capability, and an explicit ownership grant.
4. **Scorer:** sees DUT results and golden truth only after the interaction.

The only permitted vault-to-DUT information paths are the same paths available
in hardware: observed pins, passage of time, front-end fault signals, and an
explicit host grant. Protocol name, selected candidate, expected response,
secret parameters, and scorer labels may not appear on a DUT port.

Candidate sets are not secrets and may cross the DUT boundary only when they
are reproducibly derived from the public passive transcript. Supplying a set
that has been pruned using the secret target is leakage.

Random seeds and selected scenarios must be logged for reproducibility, but the
selection is not made visible to the DUT during a run.

## Behavioral electrical model

The first model uses resolved SystemVerilog nets with weak pull-ups and any
number of strong low-side drivers. Host, target, and Mindreader can only drive
low or high impedance. The testbench asserts that:

- no enabled DUT output carries a logic one;
- no pin outside the inferred clock/data pair receives output enable;
- missing authorization prevents a probe;
- revocation releases both pins without waiting for a clock;
- a stuck-low clock becomes a timeout rather than a false NACK; and
- completion and every fault leave the bus released.

This is an executable mixed-signal abstraction, not SPICE. It verifies the
digital contract of a future external analog front end. It does not establish
safe voltage, clamp current, component tolerance, or real rise time.

## First implemented tranche

`open_drain_address_probe.v` emits one bounded I2C-compatible address/write
query using START, eight open-drain bits, ACK sampling, and STOP. Clock release
waits for the observed line and has a bounded timeout.

`two_candidate_i2c_interrogator.v` receives two visible address hypotheses that
predict different outcomes for the proposed query. It probes candidate A and
uses ACK versus NACK to retain exactly one candidate. Authorization gates the
pad output enable combinationally.

The simulation-only `open_drain_target_model.sv` contains the secret address.
The randomized RTL test generates sixteen deterministic candidate pairs,
randomly instantiates A or B behind the wall, and verifies that the DUT selects
the correct survivor solely from the bus response. It also runs unauthorized,
revoked, and stuck-clock cases.

This is a real closed-loop interrogation kernel, but it is not yet an
end-to-end Mindreader claim: the public candidate pair is supplied by the test
scenario rather than produced by the integrated passive frontend, and the
kernel is not connected to the TinyTapeout top.

## Corpus-wide target

Each admitted scenario adapter must provide:

- an anonymous passive transcript;
- a learner path that derives candidates without golden labels;
- a bounded set of electrically expressible probe actions;
- behavioral host and target models;
- a scorer-only truth object;
- positive ambiguity reduction or an expected safe-refusal reason; and
- adversarial authorization, timeout, contention, and unexpected-response cases.

The randomized suite should include at least:

- selected-synchronous/SPI variants with executable response candidates;
- shared-open-drain/I2C variants;
- UART-like cases that normally refuse active interrogation;
- the stateless and stateful invented peripherals;
- length-versus-delimiter and representation-equivalence adversaries; and
- unsupported or contradictory controls.

Adapters may translate a protocol-neutral proposed action into a wire waveform,
but may not consult secret truth while choosing that action. The same proposed
action must be emitted for every target still inside the public equivalence
class.

## Closure requirements

The interrogation checkpoint remains open until:

1. candidate generation comes from integrated passive evidence;
2. the open-drain kernel is behind the top-level safety/admission boundary;
3. at least one randomized positive case reduces real integrated ambiguity;
4. every suite member either resolves or returns its expected safe refusal;
5. all electrical commands pass through the same front-end contract; and
6. the randomized suite demonstrates that changing the secret while keeping
   public evidence constant does not change the proposed probe.
