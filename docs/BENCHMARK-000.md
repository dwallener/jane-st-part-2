# BENCHMARK-000: Generated Honest Scorecard

**Status:** report generator implemented  
**Date:** 2026-09-30

Run:

```sh
python3 experiments/minimum_mindreader/run_benchmark_report.py
python3 experiments/minimum_mindreader/run_benchmark_report.py --json
```

The generator emits one row for each of the thirteen known-protocol cases and
six adversarial invented cases. Every row includes stage reached, observations
required, surviving equivalence, held-out result, replay result, refusal
reason, and unsupported claims. Fields are mandatory even when the honest
answer is “ambiguous,” “not applicable,” or “none.”

The current score is intentionally uneven: SPI reaches learned wire emulation;
UART reaches symbol decoding but retains six framing interpretations; I²C
reaches unique frame decoding but refuses emulation without open-drain
ownership proof. Exact replay fails every genuinely unseen value.
