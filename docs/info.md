## How it works

Protocol Doppelganger is a bounded autonomous protocol learner. In this first
wire-facing configuration it passively observes an anonymous four-pin SPI-like
bus, infers select and clock roles plus their physical conventions, learns a
compact request-to-response relation in both possible data directions, and
retains uncertainty until one direction is uniquely executable.

The learned model does not gain electrical authority automatically. Promotion
requires resolved direction, stream-causal response expressions, an observed
safe timing envelope, and explicit ownership authorization. Activation is a
second operation. Revocation, contradiction, reset, TinyTapeout disable, or
pad-loopback contention releases the protocol output immediately.

The implementation is deliberately bounded: one four-pin, eight-bit SPI frame
family and a response expression made from constants, copied request bits, or
inverted request bits. It is an executable demonstration of autonomous
protocol inference, not a claim to infer every possible protocol.

## Pin interface

All eight `uio` pins are passively observed for activity and quiet detection.
The current behavioral learner consumes `uio[3:0]` and determines which of
those four pins is select, clock, request data, and response data. `uio[7:4]`
participate in passive electrical observation but are never driven.

Dedicated inputs are control strobes or levels:

| Pin | Function |
| --- | --- |
| `ui[0]` | capture one discovery frame |
| `ui[1]` | observe behavioral training frames |
| `ui[2]` | promote the current learned model |
| `ui[3]` | grant electrical ownership |
| `ui[4]` | activate an admitted model |
| `ui[5]` | revoke emulation |
| `ui[6]` | clear a released fault |
| `ui[7]` | inject/report a contradictory observation |

Dedicated outputs report:

| Pin | Function |
| --- | --- |
| `uo[0]` | physical convention inference complete |
| `uo[1]` | request/response direction resolved |
| `uo[2]` | frozen model valid |
| `uo[3]` | protocol drive authorized |
| `uo[4]` | all eight observed pins quiet for the configured interval |
| `uo[5]` | timing evidence admissible |
| `uo[6]` | contention fault latched |
| `uo[7]` | latest promotion request rejected |

## How to test

Hold reset low for two clocks, then present one complete frame while `ui[0]` is
high. Drop `ui[0]`; `uo[0]` asserts when the physical convention is unique.
Present varied request/response frames with `ui[1]` high until `uo[1]` and
`uo[5]` assert. `uo[4]` independently reports that no observed pin has
changed for the configured quiet interval. Pulse `ui[2]` while holding `ui[3]`;
then assert `ui[4]`.
`uo[2]` and `uo[3]` indicate that the frozen model is executing. A new valid
request from the learned family should receive a synthesized response on the
inferred response pin.

For safe bench use, provide pad loopback on the response input path. If the
observed pad level disagrees with the driven level, output enable disappears
combinationally and `uo[6]` latches.

## External hardware

An external controller or logic analyzer must provide the observed bus traffic
and control inputs. Electrical level shifting and ownership discipline remain
the responsibility of the test setup.
