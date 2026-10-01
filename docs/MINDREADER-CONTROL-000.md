# MINDREADER-CONTROL-000: Probes, State, and Inspectability

**Status:** bounded control-plane kernels implemented  
**Date:** 2026-09-30

`active_probe_controller.v` searches all 256 requests in the learned guard and
proposes the first value on which two executable candidates disagree. Proposal
is passive; a transmit pulse is impossible without a separate authorization.
An observed answer is accepted only after that authorized transmission and
eliminates incompatible candidates. An answer matching neither candidate is
reported as a contradiction; equivalent answers preserve ambiguity.

`stateful_program_executor.v` loads up to four canonical ten-byte transitions,
matches guards in the current state, emits the selected response, and commits
the next state atomically. Unknown or ambiguous requests never mutate state.

`mindreader_status.v` exposes supervisor and fault state, physical/direction/
causality/timing/ownership flags, evidence count, survivor count, requested
probe kind, trace loss, contradiction, and contention through a small indexed
read interface.
