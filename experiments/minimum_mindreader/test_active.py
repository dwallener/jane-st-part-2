import unittest

from active_model import HypothesisSet, expand_hypotheses
from model import TimedResponse, Transaction
from synthetic_peripheral import HELD_OUT_REQUEST, observe, respond


def sparse_evidence() -> tuple[Transaction, ...]:
    return (observe(0xA0), observe(0xAF))


class ActiveDisambiguationTest(unittest.TestCase):
    def test_sparse_evidence_preserves_all_candidates(self) -> None:
        hypotheses = expand_hypotheses(sparse_evidence())

        self.assertEqual(len(hypotheses.candidates), 256)
        self.assertFalse(hypotheses.is_resolved)

    def test_probe_is_new_and_inside_learned_family(self) -> None:
        hypotheses = expand_hypotheses(sparse_evidence())
        suggestion = hypotheses.suggest_probe()

        assert suggestion is not None
        self.assertNotIn(suggestion.request, hypotheses.observed_requests)
        self.assertEqual(suggestion.request & 0xF0, 0xA0)
        self.assertLess(suggestion.worst_case_remaining, len(hypotheses.candidates))

    def test_active_loop_converges_to_held_out_model(self) -> None:
        hypotheses = expand_hypotheses(sparse_evidence())
        probes = []

        while not hypotheses.is_resolved:
            suggestion = hypotheses.suggest_probe()
            self.assertIsNotNone(suggestion)
            assert suggestion is not None
            peripheral_response = respond(suggestion.request)
            self.assertIsNotNone(peripheral_response)
            assert peripheral_response is not None
            probes.append(suggestion.request)
            hypotheses = hypotheses.observe(suggestion.request, peripheral_response)

        self.assertLessEqual(len(probes), 4)
        self.assertNotIn(HELD_OUT_REQUEST, probes)
        assert hypotheses.resolved_model is not None
        self.assertEqual(
            hypotheses.resolved_model.emulate(HELD_OUT_REQUEST),
            TimedResponse(0x67, 6),
        )

    def test_contradictory_observation_eliminates_all_candidates(self) -> None:
        hypotheses = expand_hypotheses(sparse_evidence())
        suggestion = hypotheses.suggest_probe()
        assert suggestion is not None

        contradicted = hypotheses.observe(
            suggestion.request,
            TimedResponse(0xFF, 99),
        )
        self.assertTrue(contradicted.is_contradictory)
        self.assertIsNone(contradicted.suggest_probe())

    def test_indistinguishable_candidates_have_no_probe(self) -> None:
        resolved = expand_hypotheses(
            tuple(observe(request) for request in (0xA0, 0xA1, 0xA2, 0xA4, 0xA8, 0xAF))
        )
        assert resolved.resolved_model is not None
        duplicate = HypothesisSet(
            (resolved.resolved_model, resolved.resolved_model),
            resolved.observed_requests,
        )

        self.assertIsNone(duplicate.suggest_probe())

    def test_candidate_limit_is_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "more than 100"):
            expand_hypotheses(sparse_evidence(), max_candidates=100)


if __name__ == "__main__":
    unittest.main()

