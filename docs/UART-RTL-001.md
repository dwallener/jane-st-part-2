# UART-RTL-001: Passive Concurrent Symbol Hypotheses

**Status:** integrated and tested  
**Date:** 2026-10-01

## Claim

The TinyTapeout-facing machine can passively observe one UART-like frame on an
unknown one-of-eight pin and retain every compatible bounded symbol
interpretation. It does not require the pin number, idle polarity, bit period,
data width, parity mode, or stop count to be supplied in advance.

The RTL searches this finite hypothesis space:

- physical pin: any one of eight;
- idle level: inferred from the level before the first edge;
- bit period: 2 through 16 system clocks;
- data width: 5 through 9 bits;
- parity: none, even, or odd; and
- stop count: one or two.

Capture maintains the period candidates concurrently. When observation ends,
one shared evaluator checks the 450 period/width/parity/stop combinations over
450 clocks. This time-multiplexed search produces the same exhaustive result
without synthesizing hundreds of parallel framing decoders.

`src/uart_symbol_hypothesis.v` retains the measured parallel implementation as
an unlisted reference module named `uart_symbol_hypothesis_parallel`.
`src/uart_symbol_hypothesis_seq.v` is the implementation included in the
TinyTapeout source manifest.

Surviving alternatives are exported as masks and an interpretation count. A
trace may therefore produce a useful result while remaining ambiguous. The
machine does not turn ambiguity into a guessed configuration.

## Refusal and safety boundary

This block is passive. It has no output-data or output-enable port. If more
than one physical pin changes during the observation window, pin identity is
refused rather than guessed. A UART candidate cannot authorize promotion,
ownership, activation, or electrical drive in the existing SPI execution
path.

This first implementation consumes one bounded observation window. It does not
yet intersect hypotheses across multiple frames, infer byte order above the
symbol level, identify higher-level packet boundaries, learn UART responses,
or transmit. The decoded-value status pages are meaningful only when exactly
one interpretation survives.

## Verification

The focused RTL test covers normal-idle and inverted-idle frames on different
physical pins plus a two-active-pin refusal case. The TinyTapeout top-level
test presents an 8N1 frame on physical pin 3, checks that period 4, width 8,
no parity, and one stop bit remain compatible, confirms that the SPI learner
does not complete, and continuously requires all eight output enables to stay
low.
