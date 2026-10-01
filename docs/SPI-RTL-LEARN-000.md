# SPI-RTL-LEARN-000: Passive Physical Inference in Hardware

**Status:** bounded physical learner implemented  
**Date:** 2026-09-30

`spi_physical_learner.v` consumes one anonymous four-pin waveform while every
pin remains an input. It evaluates every ordered select/clock pair from observed
transition structure, rejects clock activity outside selection, requires one
eight-bit clock burst, derives select polarity and clock idle level from the
baseline, and selects the clock edge on which both remaining data pins are
stable.

The hardware intentionally returns the two remaining data pins as an unordered
pair. Physical timing cannot establish causal direction or bit-order naming;
those symmetries must be resolved—or retained—by joint behavioral evidence.

The regression covers all four SPI modes in both corpus bit orders plus a full
pin permutation. Every case yields one select/clock/timing candidate and the
correct unordered data pair.
