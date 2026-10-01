# PROVENANCE-000: Evidence, Equivalence, and Missing Knowledge

**Status:** compact learned-model sidecar implemented  
**Date:** 2026-09-30  
**Decision gate:** distinguish supported conclusions, harmless representation
symmetries, and uncertainty that requires new evidence

## Separation from execution

The real-time SPI artifact remains 22 bytes. Provenance is a separate sidecar
so emulation does not pay the storage or lookup cost when explanation is not
needed on chip.

The first sidecar stores:

- model origin: learned, hand-authored, or host-refined;
- one 32-bit fingerprint per evidence waveform;
- typed claims with a status and 16-bit evidence-support bitmap; and
- an optional typed probe describing the missing observation.

The 32-bit fingerprints are compact identity hints, not cryptographic evidence
authentication. Full traces or strong hashes can remain on the host.

## Claim statuses

Three statuses have intentionally different meanings:

- `SUPPORTED`: the cited observations select this conclusion;
- `EQUIVALENT`: multiple descriptions remain but generate the same wire
  behavior; and
- `UNRESOLVED`: materially different behaviors or causal explanations remain.

For the lossy SPI corpus, all eight observations support physical topology,
data direction, and the behavioral transition. Bit order is marked
`EQUIVALENT`, not unresolved, and no probe is requested.

## Missing-evidence result

For the reversible SPI control, voltage behavior cannot identify which data
endpoint is the causal requester. Data direction and the behavioral transition
are marked `UNRESOLVED`. Bit order remains `EQUIVALENT`.

Trying more byte values cannot necessarily break a bijective symmetry. The
sidecar therefore requests:

```text
OBSERVE_DRIVE_OWNERSHIP
```

That means electrical direction or endpoint ownership is the missing evidence;
issuing another ordinary value probe would be misleading.

## Size

For eight evidence waveforms and four claims:

| Component | Bytes |
| --- | ---: |
| Header, origin, counts, probe type | 8 |
| Eight 32-bit evidence fingerprints | 32 |
| Four claim/status/support records | 16 |
| **Sidecar total** | **56** |

The executable core plus sidecar is 78 bytes. The core alone remains 22 bytes.
This makes provenance an explicit product choice: keep it on chip for a few
models, stream it to a host, or retain only the compact claim statuses.

## Validation

- Every claim names exactly which evidence records support it.
- Encode/decode preserves the full sidecar.
- Fingerprints change when waveform evidence changes.
- Invalid magic, truncation, and out-of-range evidence references are rejected.
- Resolved and reversible SPI corpora produce different uncertainty classes and
  probe requirements.

## Next RTL boundary

We now have enough measured structure to propose, but not yet freeze, the first
RTL memory layout:

- 22-byte executable model slot;
- live candidate masks used only during learning;
- optional streamed provenance records; and
- explicit status bits for equivalent versus unresolved candidates.

The next step is to synthesize a model-slot reader and SPI execution frontend,
then compare its area with the existing hard-wired template executor.
