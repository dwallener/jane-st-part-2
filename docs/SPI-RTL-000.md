# SPI-RTL-000: First Wire-Facing Doppelganger

**Status:** learned model executes on anonymous SPI pins  
**Date:** 2026-09-30  
**Decision gate:** prove that the learned artifact can impersonate a device at
the electrical transaction boundary

## Result

`spi_model_peripheral.v` loads the unchanged 22-byte hierarchical artifact and
uses its physical descriptor to remap four anonymous pins into select, clock,
request data, and response data. It then executes the packed response
expressions while an external master clocks an eight-bit SPI transfer.

The RTL regression performs a mode-1 transfer for the held-out request `0xA7`.
The peripheral drives `0x63` on the learned response pin, bit by bit, and
releases that pin immediately when select deasserts. No decoded request byte is
injected into the executor.

The same test verifies three refusal boundaries:

- a request outside the learned `0xA?` family is reported as unknown;
- a malformed serialized model is rejected by the underlying model slot; and
- a well-formed but noncausal program is distinguished from malformed input
  and is never allowed to drive the response pin.

## Execution architecture

The system clock oversamples select and the external SPI clock for transfer
bookkeeping. Prefix request bits are retained in an eight-bit shift image.
For a same-symbol COPY or INVERT expression, the current request pin is overlaid
combinationally so the response can settle during the launch-to-sample window.

This is intentionally not a claim that every SPI rate is safe. Admission proves
logical stream causality; the electrical timing probe from `CAUSALITY-000.md`
must still establish the usable clock envelope.

## Speculative guard behavior

Some request-family predicates are not fully known until late in a transfer.
The device may therefore need to emit early response bits speculatively and can
only report an out-of-family request at completion. The present learned
response has constant early bits, so the valid and invalid examples remain
benign, but guard-decision time is the next analysis axis for arbitrary models.
