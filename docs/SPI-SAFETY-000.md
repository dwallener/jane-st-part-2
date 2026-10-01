# SPI-SAFETY-000: Timing, Contention, and Exact Framing

**Status:** bounded safety monitors implemented  
**Date:** 2026-09-30

The decoder now accepts a transaction only when deselection proves it contains
exactly eight samples. Truncated and overlong frames abort, empty select glitches
are ignored, reset discards partial state, and immediately adjacent exact frames
are accepted independently.

`spi_timing_guard.v` measures select-to-first-sample and adjacent clock-edge
intervals against configured implementation minima. Violations are sticky.
Model promotion rejects an otherwise complete and ownership-authorized model
while this gate is unsafe.

`pin_contention_monitor.v` compares driven data with pad loopback. A mismatch
removes drive permission combinationally and latches a fault. This claim
requires a platform whose input path reflects the pad while output-enabled.
