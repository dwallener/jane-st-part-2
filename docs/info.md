## How it works

Protocol Doppelganger is a bounded autonomous protocol learner. In this first
wire-facing configuration it passively observes eight anonymous pins. It can
retain UART-like symbol hypotheses on an unknown single pin or find a
four-wire SPI-like link, infer select and clock roles plus their physical
conventions, and learn a
compact request-to-response relation in both possible data directions, and
retains uncertainty until one direction is uniquely executable.

The learned model does not gain electrical authority automatically. Promotion
requires resolved direction, stream-causal response expressions, an observed
safe timing envelope, and explicit ownership authorization. Activation is a
second operation. Revocation, contradiction, reset, TinyTapeout disable, or
pad-loopback contention releases the protocol output immediately.

The implementation is deliberately bounded: one four-wire, eight-bit SPI frame
family and a response expression made from constants, copied request bits, or
inverted request bits. It is an executable demonstration of autonomous
protocol inference, not a claim to infer every possible protocol.

## Pin interface

All eight `uio` pins are passively observed. The current behavioral learner
finds which four carry the bounded SPI-like link and determines select, clock,
request-data, and response-data roles. No pin is driven before model admission,
explicit ownership, and activation; only the inferred response pin can then
acquire output enable.

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
| `ui[7]` | passive status mode while `ui[4]=0`; contradiction while `ui[4]=1` |

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

When `ui[7]=1` and `ui[4]=0`, normal status is replaced by a passive 16-page
window. The page address is `{ui[3:2], ui[6:5]}`; all command meanings on
those four pins are suppressed while the window is active. `ui[4]=1` leaves
status mode and retains its normal activate/contradiction meaning.

| Page | Input byte | Status returned on `uo[7:0]` |
| --- | --- | --- |
| `0` | `80` | eight-pin activity mask |
| `1` | `A0` | clocks since the latest transition, saturating at the quiet threshold |
| `2` | `C0` | ambiguity, insufficiency, quiet, router-ready, activity-seen, and three structural candidate bits |
| `3` | `E0` | structural clock-candidate mask |
| `4` | `84` | UART-compatible interpretation count, low eight bits |
| `5` | `A4` | UART ready, valid, ambiguous, pin-valid, idle level, and physical pin index |
| `6` | `C4` | UART bit-period candidates 2 through 9 |
| `7` | `E4` | UART bit-period candidates 10 through 16 |
| `8` | `88` | UART data-width candidates 5 through 9 |
| `9` | `A8` | UART parity candidates (none/even/odd) and stop-count candidates (one/two) |
| `A` | `C8` | UART-compatible interpretation count, high two bits |
| `B` | `E8` | decoded value, low eight bits; meaningful only for a unique candidate |
| `C` | `8C` | decoded value bit eight; meaningful only for a unique candidate |
| `D`–`F` | — | reserved (`FF`) |

The structural candidate bits are asynchronous single-wire, selected
synchronous, and shared two-wire clocked. They are intentionally nonexclusive.
The UART bank likewise retains all compatible framing interpretations. Neither
surface authorizes pin drive.

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
