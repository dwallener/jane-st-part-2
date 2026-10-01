import unittest
from adversarial_corpus import run_adversarial_corpus

class AdversarialCorpusTest(unittest.TestCase):
    def test_every_required_dimension_has_a_passing_negative_control(self):
        results = run_adversarial_corpus()
        dimensions = {dimension for result in results for dimension in result.dimensions}
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(dimensions, {
            "variable_width", "length_framing", "delimiter_framing", "integrity",
            "state", "ambiguity", "corrupted_trace", "causally_impossible",
        })
        self.assertTrue(any(result.refusal for result in results))

    def test_corpus_is_not_a_collection_of_success_only_examples(self):
        results = run_adversarial_corpus()
        refusals = {result.name for result in results if result.refusal}
        self.assertEqual(refusals, {
            "length_or_delimiter", "crc_with_corruption",
            "future_bit_dependency", "mixed_width_contradiction",
        })
