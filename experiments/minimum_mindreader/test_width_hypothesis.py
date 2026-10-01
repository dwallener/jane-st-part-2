import unittest

from framing_hypothesis import FramingHypothesis, PinRoles
from model import Transaction
from synthetic_link import CLOCK, REQUEST_DATA, RESPONSE_DATA, RESPONSE_VALID, SELECT
from synthetic_peripheral import training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant, remap_pins
from width_hypothesis import PhaseShape, infer_width, observe_phase_shape


class WidthHypothesisTest(unittest.TestCase):
    def test_eight_bit_phases_have_four_symbol_granularities(self) -> None:
        hypothesis = FramingHypothesis(SamplingEdge.RISING, BitOrder.MSB_FIRST)
        traces = tuple(
            encode_variant(item, SamplingEdge.RISING, BitOrder.MSB_FIRST)
            for item in training_corpus()
        )

        result = infer_width(traces, hypothesis, PinRoles())

        self.assertEqual(result.phase_shape, PhaseShape(8, 8))
        self.assertEqual(result.symbol_widths, (1, 2, 4, 8))
        self.assertEqual(result.symbols_per_request(4), 2)
        self.assertEqual(result.symbols_per_request(8), 1)

    def test_six_bit_fixture_is_not_hard_coded_to_bytes(self) -> None:
        hypothesis = FramingHypothesis(SamplingEdge.FALLING, BitOrder.LSB_FIRST)
        traces = tuple(
            encode_variant(
                Transaction(request, request ^ 0x15, 4),
                SamplingEdge.FALLING,
                BitOrder.LSB_FIRST,
                frame_width=6,
            )
            for request in (0x00, 0x03, 0x0C, 0x2A)
        )

        result = infer_width(traces, hypothesis, PinRoles())

        self.assertEqual(result.phase_shape, PhaseShape(6, 6))
        self.assertEqual(result.symbol_widths, (1, 2, 3, 6))

    def test_permuted_roles_preserve_width_observation(self) -> None:
        roles = PinRoles(
            clock=0x04,
            request_data=0x01,
            select=0x02,
            response_data=0x02,
            response_valid=0x01,
        )
        trace = remap_pins(
            encode_variant(
                training_corpus()[0], SamplingEdge.FALLING, BitOrder.MSB_FIRST
            ),
            input_mapping={
                CLOCK: roles.clock,
                REQUEST_DATA: roles.request_data,
                SELECT: roles.select,
            },
            output_mapping={
                RESPONSE_DATA: roles.response_data,
                RESPONSE_VALID: roles.response_valid,
            },
        )
        hypothesis = FramingHypothesis(SamplingEdge.FALLING, BitOrder.MSB_FIRST)

        self.assertEqual(observe_phase_shape(trace, hypothesis, roles), PhaseShape(8, 8))

    def test_wrong_sampling_edge_is_rejected(self) -> None:
        trace = encode_variant(
            training_corpus()[1], SamplingEdge.RISING, BitOrder.MSB_FIRST
        )
        wrong = FramingHypothesis(SamplingEdge.FALLING, BitOrder.MSB_FIRST)

        with self.assertRaisesRegex(ValueError, "sampling edge"):
            observe_phase_shape(trace, wrong, PinRoles())

    def test_variable_phase_width_corpus_is_explicitly_rejected(self) -> None:
        hypothesis = FramingHypothesis(SamplingEdge.RISING, BitOrder.MSB_FIRST)
        traces = (
            encode_variant(
                Transaction(0x2A, 0x15, 4),
                SamplingEdge.RISING,
                BitOrder.MSB_FIRST,
                frame_width=6,
            ),
            encode_variant(
                Transaction(0xAA, 0x55, 4),
                SamplingEdge.RISING,
                BitOrder.MSB_FIRST,
                frame_width=8,
            ),
        )

        with self.assertRaisesRegex(ValueError, "variable framed phase widths"):
            infer_width(traces, hypothesis, PinRoles())


if __name__ == "__main__":
    unittest.main()
