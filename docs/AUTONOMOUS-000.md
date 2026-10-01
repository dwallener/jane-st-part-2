# AUTONOMOUS-000: Observe, Learn, Yield, Impersonate

**Status:** first end-to-end autonomous RTL proof implemented  
**Date:** 2026-09-30

The integrated RTL now completes the central loop without receiving a model
from software:

1. `spi_physical_learner` passively observes an anonymous transfer and recovers
   select, clock, polarity, sampling edge, and the unordered data pair.
2. `spi_transaction_decoder` uses only those inferred fields to decode later
   traffic.
3. `dual_direction_learner` trains both possible causal directions in parallel.
   The lossy corpus makes exactly one direction executable after eight frames.
4. `learned_model_promoter` checks uniqueness, stream causality, timing
   authorization, and ownership, then freezes an immutable execution snapshot.
5. `mindreader_supervisor` remains passive until explicit activation.
6. `template_spi_peripheral` answers the unseen request `0xA7` with `0x63` on
   the inferred response pin.

The regression first attempts promotion without ownership and verifies refusal.
During discovery and all eight learning transfers, every output-enable bit is
zero. Only after the original device is declared yielded, the model is frozen,
and activation is requested does the response driver become available.

This proof is bounded to one eight-bit SPI word and the current expression
language. It establishes autonomy of the learning path, not generality across
all protocols.
