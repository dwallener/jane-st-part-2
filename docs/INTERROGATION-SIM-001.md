# INTERROGATION-SIM-001: Chinese-Wall Closed-Loop Simulation

**Status:** adaptive wire-level demonstrator and first corpus-wide policy
harness implemented; TinyTapeout-top integration remains open
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

## First corpus-wide policy pass

`interrogation_harness.py` is a label-free policy boundary. Its public input
contains anonymous samples or transactions, inferred transport capability,
electrical admission, bounded resources, and allowed actions. It contains no
protocol name, golden family, target selection, expected response, or scoring
result. The response oracle is a callback that can be invoked only after the
policy has independently selected a probe.

`interrogation_oracle_suite.py` is the opposite side of the wall. It registers
all thirteen canonical waveform cases, the adversarial/invented corpus,
stateful invented evidence, and a randomized executable template family. The
host shuffles these scenarios from a reproducible seed.

The current corpus-wide result has two intentionally different meanings:

- canonical, adversarial, and currently unsupported stateful transports must
  return their exact safe-refusal class without consulting the oracle; and
- the executable invented template family begins with 256 models consistent
  with identical public evidence, hides one randomly selected model behind the
  response callback, and must resolve it in no more than four probes.

Eight randomized suite orderings currently exercise 168 scored scenarios.
Changing only the hidden model while preserving the public evidence is tested
to leave the first proposed probe unchanged. An impossible response must yield
contradiction rather than forced classification.

This is not yet wire-level coverage for every suite member. It establishes the
selection, separation, refusal, and scoring machinery into which protocol
adapters can be admitted one at a time.

## Adaptive wire-level invented protocol

The first complete passive-to-active learning loop deliberately uses an
invented protocol so neither the DUT nor its test can hide behind a known
protocol decoder. A target accepts an open-drain seven-bit request and ACKs
when one unknown request bit is one. The secret bit exists only as a parameter
of the simulation-only target model.

`open_drain_bit_learner.v` begins with fourteen hypotheses: ACK is either a
copy or inversion of one of the seven request bits. Two identical passive
observations reduce that set to the seven copy hypotheses. It then scores all
128 possible requests for the most balanced partition of the survivors,
without seeing the target or its secret. To remain plausible hardware, one
scoring datapath examines one request per clock instead of expanding all 128
possibilities into parallel combinational logic.

`adaptive_open_drain_interrogator.v` hands the selected request to the same
bounded, authorization-gated open-drain transaction engine used by the first
kernel. The observed wire ACK/NACK returns through the ordinary evidence port
and eliminates inconsistent hypotheses. This repeats until exactly one model
remains.

`adaptive_i2c_interrogation_bridge.v` removes the testbench-decoder shortcut.
It accepts raw anonymous pin samples, reuses the existing
`i2c_symbol_hypothesis.v` frontend to infer clock/data roles and decode the
request plus ACK, and admits only a unique, complete, unsaturated observation
to the adaptive learner. The active side then uses those inferred pins; no pin
number, decoded request, ACK, or candidate set is injected by the scorer.

Two randomized RTL tests cover every hidden bit position in shuffled order.
The first tests the adaptive kernel directly. The second generates the two
passive transactions as resolved open-drain wire activity, requires the
existing frontend to infer pins 2 and 5 and decode the evidence, and only then
permits active interrogation. All seven targets receive the same passive
traffic and produce the same first probe; each resolves to the correct hidden
rule in no more than three active transactions. The tests also prove
low-or-release drive and confinement to the inferred two pins. Strict
Verilator lint is clean. Standalone generic Yosys synthesis reports 651 cells
for the learner plus transaction engine and zero structural problems. The full
bridge, including a separate copy of the already-integrated parallel I2C
frontend, is 9,747 generic cells; top-level integration should reuse the
existing frontend rather than duplicate it.

Together with the policy suite, the repository regression now passes 128
tests and 266 parameterized/randomized subtests. This is the first executable
proof that Mindreader can formulate an experiment from public ambiguity,
perform it through a behavioral electrical boundary, interpret the response,
and change its mind. The same learner and wire engine are now connected to the
existing decoder inside `mindreader_core`; the top-level proof and control
contract are recorded in `INTERROGATION-INTEGRATION-001.md`. This is not yet a
routed-area claim.

`test/interrogation/adaptive_i2c_bridge_demo_tb.sv` is the deterministic visual
demonstration. It emits an intentionally untracked
`adaptive_i2c_interrogation.vcd` containing five labeled phases, the resolved
bus, inferred roles, proposal search, candidate mask/count, active-probe
handshake, and final winner. Reproduction and viewer instructions are in
`test/interrogation/WAVEFORM.md`.

## Corpus-wide target

Each admitted scenario adapter must provide:

- an anonymous passive transcript;
- a learner path that derives candidates without golden labels;
- a bounded set of electrically expressible probe actions;
- behavioral host and target models;
- a scorer-only truth object;
- positive ambiguity reduction or an expected safe-refusal reason; and
- adversarial authorization, timeout, contention, and unexpected-response cases.

The randomized suite includes registry entries for the following; entries do
not become positive active claims until their wire adapter is implemented:

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

1. ~~candidate generation comes from the TinyTapeout-integrated passive evidence;~~
2. ~~the open-drain kernel is behind the top-level safety/admission boundary;~~
3. ~~at least one randomized positive case reduces real integrated ambiguity;~~
4. ~~every suite member either resolves or returns its expected safe refusal;~~
5. all electrical commands pass through the same front-end contract; and
6. ~~the randomized suite demonstrates that changing the secret while keeping
   public evidence constant does not change the proposed probe.~~
