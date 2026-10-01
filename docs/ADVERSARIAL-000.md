# ADVERSARIAL-000: Protocols Designed to Break the Claim

The adversarial corpus is a set of executable negative controls, not a gallery
of protocols the learner is expected to emulate. Each case attacks an
assumption that a byte-oriented happy path could otherwise hide.

| Case | Pressure applied | Required outcome |
| --- | --- | --- |
| `six_bit_not_byte` | Six-bit phases with several valid divisors | Retain all compatible granularities; do not rename the phase as a byte |
| `length_or_delimiter` | Length and delimiter grammars explain the same evidence | Retain both and request a distinguishing frame |
| `crc_with_corruption` | A valid CRC family plus a corrupted held-out frame | Identify the bounded rule and reject the corruption |
| `history_changes_answer` | The same request has different answers after a transition | Infer state rather than collapse the responses |
| `future_bit_dependency` | An early response bit depends on a later request bit | Classify the model as noncausal and refuse same-frame execution |
| `mixed_width_contradiction` | Fixed-width observations disagree | Eliminate the fixed-width hypothesis rather than averaging widths |

Together these cases exercise variable width, both length and delimiter
framing, integrity, state, ambiguity, corrupted evidence, and causally
impossible behavior. `adversarial_corpus.py` runs the real bounded inference
engines used by the experiments and records observations required, surviving
equivalence, held-out behavior, and any refusal. The tests additionally require
at least one retained ambiguity and at least one explicit rejection, preventing
the corpus from degenerating into success-only examples.

This suite does not prove arbitrary-protocol inference. It demonstrates that
the bounded architecture can preserve uncertainty and refuse unsafe claims
when familiar protocol assumptions are false.
