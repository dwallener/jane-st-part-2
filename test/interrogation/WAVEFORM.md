# Adaptive interrogation waveform

Generate the deterministic VCD from the repository root:

```sh
iverilog -g2012 -s adaptive_i2c_bridge_demo_tb \
  -o /tmp/adaptive_i2c_bridge_demo.vvp \
  src/i2c_symbol_hypothesis.v \
  src/open_drain_bit_learner.v \
  src/open_drain_address_probe.v \
  src/adaptive_open_drain_interrogator.v \
  src/adaptive_i2c_interrogation_bridge.v \
  test/interrogation/models/open_drain_bit_target_model.sv \
  test/interrogation/adaptive_i2c_bridge_demo_tb.sv
vvp /tmp/adaptive_i2c_bridge_demo.vvp
```

This writes `test/interrogation/adaptive_i2c_interrogation.vcd`. The generated
file is intentionally ignored by Git.

Open it with:

```sh
gtkwave test/interrogation/adaptive_i2c_interrogation.vcd
```

or:

```sh
surfer test/interrogation/adaptive_i2c_interrogation.vcd
```

`demo_phase` is the visual index:

1. passive all-zero request and NACK;
2. passive all-one request and ACK;
3. seven-way ambiguity and proposal search;
4. authorized active probes and candidate elimination; and
5. one surviving hypothesis, followed by bus release.

The most useful signals are `scl`, `sda`, `pin_oe`, `passive_accepted`,
`inferred_clock_pin`, `inferred_data_pin`, `proposal_request`,
`candidate_mask`, `candidate_count`, `probe_done`, `resolved`, and
`winner_bit`.
