## How it works

This is the initial CMOS5L flow smoke test for Protocol Doppelganger. A portable
eight-bit counter core is wrapped by the standard Tiny Tapeout top-level module.
The dedicated output is the counter XOR the dedicated input. The bidirectional
output path is the counter plus the bidirectional input, and the lower four
bidirectional output enables are asserted while the project is enabled.

This logic is intentionally disposable. It validates the Tiny Tapeout wrapper,
clock, reset, enable, all three bidirectional paths, RTL simulation, synthesis,
place-and-route, precheck, and gate-level simulation.

## How to test

Assert active-low reset for at least one rising clock edge. With the project
enabled, release reset and observe the counter advance on each rising edge.
Deasserting the project enable forces all outputs and output enables low.

## External hardware

None.
