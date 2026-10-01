# FUTURE-ISSUES-001: Nonstationary and Concurrent Protocols

**Status:** open questions; no implementation claim
**Date:** 2026-10-01

These issues are intentionally deferred. They describe two ways the assumption
of one stationary protocol over one observation window can fail.

## FI-1: Can Mindreader change its mind?

### Question

Can the attached protocol change while Mindreader is observing it, and can the
machine prefer newer evidence over a model learned from older traffic?

Examples include a bootloader switching to an application protocol, negotiated
baud-rate or framing changes, an SPI device changing mode after configuration,
and a physical connection being repurposed without reset.

### Current behavior

Within one observation window, the passive hypothesis banks accumulate or
eliminate candidates. They do not apply recency weighting, detect a change
point, or revive a candidate eliminated by old evidence. A new capture window
can reset several passive banks, but an admitted behavioral model is not
automatically replaced merely because newer traffic appears different.
Contradiction causes refusal or fault; it does not currently mean “the protocol
has changed, begin a new epoch.”

### Future design issue

Investigate explicit evidence epochs and bounded change-point detection. A
future implementation should distinguish at least:

- ordinary noise or one contradictory observation;
- a protocol phase change already represented by a stateful model;
- renegotiation of timing or framing within the same family; and
- replacement by a genuinely different protocol.

Changing models must never silently expand drive authority. On suspected
change, the safe default is to release all outputs, retain the old model and
its provenance, begin a new passive epoch, and expose both the change reason
and the evidence supporting it.

Open questions include the history depth, hysteresis, evidence-decay policy,
model rollback, and how a host authorizes promotion of the replacement model.

## FI-2: What if two protocols use disjoint pins simultaneously?

### Question

If all eight pins are attached, can Mindreader separate two independent links
running at the same time—for example, UART on one pin and I²C on two others, or
two separate SPI-like groups?

### Current behavior

The front end observes all eight pins, but each integrated family recognizer is
currently a single-instance hypothesis bank over the joint observation. It
does not partition pins into independent traffic sources. Unrelated activity
can therefore contaminate a candidate: the UART bank refuses a unique UART pin
when another pin changes, the shared-two-wire structural route expects one
two-pin group, and extra activity can leave the selected-synchronous learner
ambiguous. The honest current result is ambiguity, insufficiency, or refusal—not
two decoded protocols.

### Future design issue

Investigate bounded source separation before or alongside family inference:

- construct an activity/correlation graph over the eight pins;
- retain multiple plausible disjoint or overlapping pin partitions;
- run a bounded number of recognizer instances per partition;
- distinguish independent protocols from multiple channels belonging to one
  protocol; and
- report resource exhaustion rather than silently dropping a second link.

The design must preserve ambiguity when two partitions explain the same
traffic, cope with time-interleaved as well as simultaneous activity, and keep
electrical ownership and authorization separate for every inferred link.

Open questions include the maximum number of concurrent links, whether shared
clock or control pins may belong to multiple groups, and how the eight-bit
status interface enumerates more than one result.

## Non-goals for the current checkpoint

Neither issue changes the claims in `CHECKPOINT-001.md`. The present machine
targets one stationary protocol interpretation at a time and refuses evidence
that violates that bounded model. Resolving FI-1 or FI-2 requires its own
acceptance tests and physical-cost review before becoming a supported claim.
