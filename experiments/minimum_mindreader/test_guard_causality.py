import unittest

from guard_causality import GuardRisk, analyze_program_guards
from hierarchical_model import build_hierarchical_spi_model
from spi_behavior import make_spi_behavior_corpus


class GuardCausalityTest(unittest.TestCase):
    def test_msb_fixture_has_only_constant_speculative_prefix(self) -> None:
        for mode in range(4):
            artifact = build_hierarchical_spi_model(
                make_spi_behavior_corpus(mode, True)
            )
            analysis = analyze_program_guards(artifact.program)[0]
            self.assertEqual(analysis.decision_time, 3)
            self.assertEqual(
                analysis.risk, GuardRisk.SPECULATIVE_CONSTANT_PREFIX
            )
            self.assertEqual(analysis.speculative_dependent_bits, ())

    def test_canonical_lsb_fixture_exposes_dependent_speculation(self) -> None:
        for mode in range(4):
            artifact = build_hierarchical_spi_model(
                make_spi_behavior_corpus(mode, False)
            )
            analysis = analyze_program_guards(artifact.program)[0]
            self.assertEqual(analysis.decision_time, 7)
            self.assertEqual(
                analysis.risk, GuardRisk.SPECULATIVE_DEPENDENT_OUTPUT
            )
            self.assertEqual(analysis.speculative_dependent_bits, (6, 7))

    def test_guard_free_program_needs_no_speculation(self) -> None:
        artifact = build_hierarchical_spi_model(make_spi_behavior_corpus(0, True))
        transition = artifact.program.transitions[0]
        guard_free = transition.__class__(
            transition.state,
            0,
            0,
            transition.response_bits,
            transition.delay_cycles,
            transition.next_state,
        )
        analysis = analyze_program_guards(
            artifact.program.__class__((guard_free,))
        )[0]
        self.assertEqual(analysis.risk, GuardRisk.GUARD_FREE)
        self.assertIsNone(analysis.decision_time)
