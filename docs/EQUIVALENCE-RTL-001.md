# EQUIVALENCE-RTL-001: Report Meanings, Not Brand Names

**Status:** integrated and tested  
**Date:** 2026-10-01

## Interpretation mask

The classifier waits until the structural router, UART candidate search,
shared-two-wire learner, and generic event framer are all ready. It then emits
one bit for every interpretation supported by both routing and deeper evidence:

| Bit | Surviving interpretation |
| --- | --- |
| `0` | asynchronous single-wire symbols compatible with the UART-like bank |
| `1` | selected synchronous framing with resolved physical roles |
| `2` | shared two-wire byte/ACK framing |
| `3` | two-edge control enclosure |
| `4` | quiet-gap frame separation |
| `5` | equal event count across gap-separated bursts |

The output is not a priority encoder. A trace can support several meanings at
once. Separate flags distinguish exactly one survivor, multiple equivalent
survivors, no supported survivor, and inference that is not ready yet.

## Product-boundary demonstration

The generic two-burst top-level trace retains bits 4 and 5 simultaneously.
The reported count is two, `equivalent` is asserted, and both `unique` and
`insufficient` remain clear. The report is available through passive status
pages and cannot change output enable.

This closes classification only at the currently integrated structural level.
It does not claim semantic equivalence between arbitrary application protocols,
nor does it discard the detailed parameter masks maintained by each frontend.

## Refusal matrix

The integrated negative-control test distinguishes absence of evidence from
contradiction and malformed framing without converting any of them into a
guess. It covers silence, incomplete selected framing, contaminated
single-wire traffic, missing shared-two-wire termination, and unequal generic
bursts. The status result changes, but electrical authority never does.
