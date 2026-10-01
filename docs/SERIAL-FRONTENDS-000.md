# SERIAL-FRONTENDS-000: UART and I²C Without Labels

The UART frontend enumerates idle polarity, bit period, five-to-nine data bits,
parity compatibility, and one/two stop bits across anonymous one-pin traces.
It recovers the canonical 8N1 interpretation and retains every alternative
still consistent with the samples. A malformed-stop negative control removes
the canonical 8N1 candidate instead of decoding a plausible-looking symbol.

The I²C frontend tries both anonymous two-pin role assignments, recognizes
start/stop and rising-edge groups, extracts bytes and ACK ownership positions,
and records that any executor must use open-drain behavior. The golden write
uniquely recovers clock pin 0, data pin 1, bytes `A0 2A`, and two ACK lows. A
generated write-then-read fixture contains a repeated start; the decoder emits
two frames while preserving the repeated-start boundary and ACK ownership.

These are inference frontends, not complete bus implementations. UART transmit
timing and session behavior remain unsupported. I²C emulation remains refused
until open-drain ownership is proven; arbitration, clock stretching, and
electrical timing are outside the present claim.
