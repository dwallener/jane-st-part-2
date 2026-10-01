# SUPERVISOR-000: Passive Until Proven Safe

**Status:** first fail-safe authority and trace-capture boundary implemented  
**Date:** 2026-09-30

`mindreader_supervisor.v` implements `OBSERVE`, `CANDIDATE`, `ADMITTED`,
`EMULATE`, and latched `FAULT` states. Reset, candidates, and admitted models
are electrically passive. Driving requires a complete model, resolved
direction, stream causality, adequate timing, explicit ownership, and explicit
activation simultaneously.

Drive enable is qualified combinationally. Revocation, contradiction, or
contention therefore removes authority without waiting for another clock. A
contention or contradiction also enters a latched fault; clearing it restarts
observation rather than resuming an old model.

`edge_trace_capture.v` records cycle delta, complete anonymous pin sample, and
changed mask into a bounded FIFO. Counter saturation or FIFO overflow sets a
sticky loss flag and makes `evidence_valid` false. Lost evidence can never be
mistaken for a complete trace.

The RTL regression proves reset passivity, gated promotion, immediate revoke,
contention faulting, ordered trace records, overflow poisoning, and explicit
recovery.
