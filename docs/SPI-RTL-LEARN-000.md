# SPI-RTL-LEARN-000: Passive Physical Inference in Hardware

**Status:** bounded physical learner implemented  
**Date:** 2026-09-30

`spi_physical_learner.v` consumes one anonymous eight-pin waveform while every
pin remains an input. A four-wire SPI link may occupy any subset. The learner
evaluates every ordered select/clock pair from observed transition structure,
rejects clock activity outside selection, requires one eight-bit clock burst,
derives select polarity and clock idle level from the baseline, and selects the
clock edge on which the candidate data pins are stable.

The two remaining active pins become the unordered data pair. Both must
transition at least once in the discovery frame. A constant data line or an
unrelated fifth active pin leaves physical inference incomplete instead of
silently choosing a convenient subset.

The hardware intentionally returns the two remaining data pins as an unordered
pair. Physical timing cannot establish causal direction or bit-order naming;
those symmetries must be resolved—or retained—by joint behavioral evidence.

The regression covers all four SPI modes in both corpus bit orders plus a
mapping onto physical pins 6, 1, 7, and 4. Every positive case yields one
select/clock/timing candidate and the correct unordered data pair. Negative
controls cover a constant data line and an extra active pin; both retain
ambiguity and refuse completion.
