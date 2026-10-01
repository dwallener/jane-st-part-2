import unittest

from hierarchical_model import build_hierarchical_spi_model
from model import BitExpression, ExpressionKind
from protocol_program import GuardedTransition, ProtocolProgram
from spi_behavior import make_spi_behavior_corpus
from spi_causality import (
    CausalityClass,
    TimingRequirement,
    analyze_spi_causality,
)
from spi_hypothesis import SpiBitOrder, SpiSamplingEdge


def program_with_dependency(response_bit: int, request_bit: int) -> ProtocolProgram:
    expressions = [BitExpression(ExpressionKind.CONSTANT, 0) for _ in range(8)]
    expressions[response_bit] = BitExpression(ExpressionKind.COPY, request_bit)
    return ProtocolProgram(
        (
            GuardedTransition(
                state=0,
                request_mask=0,
                request_value=0,
                response_bits=tuple(expressions),
                delay_cycles=0,
                next_state=0,
            ),
        )
    )


class SpiCausalityTest(unittest.TestCase):
    def test_learned_spi_relation_is_same_symbol_causal_for_every_variant(self) -> None:
        for mode in range(4):
            for msb_first in (True, False):
                with self.subTest(mode=mode, msb_first=msb_first):
                    artifact = build_hierarchical_spi_model(
                        make_spi_behavior_corpus(mode, msb_first)
                    )
                    analysis = analyze_spi_causality(
                        artifact.program,
                        sampling_edge=artifact.physical.sampling_edge,
                    )
                    self.assertEqual(
                        analysis.classification,
                        CausalityClass.SAME_SYMBOL_CAUSAL,
                    )
                    self.assertTrue(analysis.executable_in_one_frame)
                    self.assertIn(
                        TimingRequirement.LAUNCH_TO_SAMPLE,
                        analysis.timing_requirements,
                    )
                    needs_select_setup = mode in (0, 2) and not msb_first
                    self.assertEqual(
                        TimingRequirement.SELECT_TO_FIRST_SAMPLE
                        in analysis.timing_requirements,
                        needs_select_setup,
                    )

    def test_constant_response_is_precomputable(self) -> None:
        analysis = analyze_spi_causality(program_with_dependency(0, 0))
        constant_expressions = tuple(
            BitExpression(ExpressionKind.CONSTANT, 1) for _ in range(8)
        )
        constant_program = ProtocolProgram(
            (
                GuardedTransition(0, 0, 0, constant_expressions, 0, 0),
            )
        )
        self.assertEqual(
            analyze_spi_causality(constant_program).classification,
            CausalityClass.PRECOMPUTABLE,
        )
        self.assertEqual(
            analysis.classification, CausalityClass.SAME_SYMBOL_CAUSAL
        )

    def test_earlier_request_bit_is_prefix_causal(self) -> None:
        analysis = analyze_spi_causality(program_with_dependency(0, 7))
        self.assertEqual(analysis.classification, CausalityClass.PREFIX_CAUSAL)
        self.assertEqual(analysis.dependencies[0].offset, 7)

    def test_future_request_bit_is_noncausal(self) -> None:
        analysis = analyze_spi_causality(program_with_dependency(7, 0))
        self.assertEqual(analysis.classification, CausalityClass.NONCAUSAL)
        self.assertFalse(analysis.executable_in_one_frame)
        self.assertEqual(
            analysis.timing_requirements,
            (TimingRequirement.FUTURE_REQUEST_BIT,),
        )

    def test_first_cpha_zero_same_symbol_needs_select_setup(self) -> None:
        program = program_with_dependency(7, 7)
        leading = analyze_spi_causality(
            program,
            bit_order=SpiBitOrder.MSB_FIRST,
            sampling_edge=SpiSamplingEdge.LEADING,
        )
        trailing = analyze_spi_causality(
            program,
            bit_order=SpiBitOrder.MSB_FIRST,
            sampling_edge=SpiSamplingEdge.TRAILING,
        )
        self.assertIn(
            TimingRequirement.SELECT_TO_FIRST_SAMPLE,
            leading.timing_requirements,
        )
        self.assertNotIn(
            TimingRequirement.SELECT_TO_FIRST_SAMPLE,
            trailing.timing_requirements,
        )
