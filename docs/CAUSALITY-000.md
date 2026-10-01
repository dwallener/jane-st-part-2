# CAUSALITY-000: Can the Learned Response Arrive in Time?

**Status:** dependency causality implemented; electrical margin unmeasured  
**Date:** 2026-09-30  
**Decision gate:** separate correct word-level prediction from physically
possible same-frame impersonation

## Why this exists

A learned mapping can correctly say that request `A7` produces response `63`
and still be impossible to execute as an SPI slave. If the first response bit
depends on the last request bit, the information arrives seven symbols too
late. This is not a faster-RTL problem; it is causally impossible within the
same frame.

The analyzer assigns each response expression to one of four classes:

| Class | Meaning |
| --- | --- |
| `precomputable` | Every response bit is constant before selection. |
| `prefix_causal` | Each dependent request bit was observed earlier. |
| `same_symbol_causal` | At least one response bit uses the request bit launched for the same symbol; a launch-to-sample timing budget is required. |
| `noncausal` | A response bit requires a future request bit and cannot be emitted in the observed frame. |

Copy and invert expressions have the same dependency timing. Constants have no
request dependency.

## Result on the learned corpus

All eight SPI mode/order fixtures classify as `same_symbol_causal`. The learned
relation `response = 0x60 | request[1:0]` never needs a future request bit, so a
same-frame pin-level executor is possible in principle. It does require enough
time between the data-launch event and the sampling event to capture the
request bit, evaluate its expression, and settle the response pin.

The mode/order cross-product exposes a subtlety that word-level testing hides.
For the MSB-first fixture the dependent low bits occur late. Canonicalizing an
LSB-first fixture by bit reversal moves those dependencies to the first wire
symbols. Consequently, CPHA=0 LSB fixtures also require a
select-to-first-sample timing path, while CPHA=1 has a leading launch edge
before its trailing sampling edge. The regression checks this distinction for
all eight variants.

## Honest remaining unknown

Waveform topology tells us edge order, not analog setup/hold margin or the
maximum safe clock rate. The next active experiment is therefore a timing
probe, not another value probe: vary the launch-to-sample interval and retain
the fastest interval that remains stable. A model should be admitted to the
pin-level executor only when its dependency class and measured timing budget
fit the implementation path.

`SPI-RTL-000.md` implements the first such admission gate: a well-formed
noncausal program remains inspectable but cannot enable any response driver.
