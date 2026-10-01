import dataclasses
import random
import unittest

from interrogation_harness import RefusalCode, interrogate
from interrogation_oracle_suite import make_template_scenario, scenario_suite


class InterrogationSuiteTest(unittest.TestCase):
    def test_randomized_corpus_resolves_or_refuses_honestly(self) -> None:
        for seed in range(8):
            scenarios = scenario_suite(random.Random(seed))
            labels = {scenario.label for scenario in scenarios}
            self.assertTrue(any(label.startswith("canonical:") for label in labels))
            self.assertTrue(any(label.startswith("adversarial:") for label in labels))
            self.assertIn("invented_mask_template", labels)
            for scenario in scenarios:
                with self.subTest(seed=seed, scenario=scenario.label):
                    result = interrogate(scenario.public, scenario.exchange)
                    self.assertEqual(result.resolved, scenario.should_resolve)
                    self.assertEqual(result.refusal, scenario.expected_refusal)
                    if result.resolved:
                        self.assertGreater(len(result.probes), 0)
                        self.assertLessEqual(len(result.probes), 4)
                    else:
                        self.assertEqual(result.probes, ())

    def test_public_view_contains_no_labels_or_secret_selection(self) -> None:
        scenario = make_template_scenario(173)
        public_fields = {field.name for field in dataclasses.fields(scenario.public)}
        forbidden = {"label", "name", "family", "truth", "secret", "selected"}
        self.assertTrue(public_fields.isdisjoint(forbidden))
        self.assertFalse(hasattr(scenario.public, "exchange"))
        self.assertFalse(hasattr(scenario.public, "expected_refusal"))

    def test_secret_cannot_change_first_probe(self) -> None:
        left = make_template_scenario(0)
        right = make_template_scenario(255)
        self.assertEqual(left.public, right.public)

        left_result = interrogate(left.public, left.exchange)
        right_result = interrogate(right.public, right.exchange)
        self.assertTrue(left_result.resolved)
        self.assertTrue(right_result.resolved)
        self.assertEqual(left_result.probes[0], right_result.probes[0])
        self.assertNotEqual(left_result.probes, ())

    def test_contradictory_oracle_is_not_forced_into_a_candidate(self) -> None:
        scenario = make_template_scenario(0)

        def impossible_response(_: int):
            from model import TimedResponse

            return TimedResponse(0xFF, 99)

        result = interrogate(scenario.public, impossible_response)
        self.assertFalse(result.resolved)
        self.assertEqual(result.refusal, RefusalCode.CONTRADICTORY_RESPONSE)
        self.assertGreater(len(result.probes), 0)


if __name__ == "__main__":
    unittest.main()
