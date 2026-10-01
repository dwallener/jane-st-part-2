import unittest

from framing_hypothesis import FramingHypothesis, decode_with_hypothesis, infer_framing
from model import TimedResponse
from synthetic_peripheral import HELD_OUT_REQUEST, training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant


def reverse_byte(value: int) -> int:
    return int(f"{value:08b}"[::-1], 2)


class FramingHypothesisTest(unittest.TestCase):
    def _infer(self, edge: SamplingEdge, order: BitOrder):
        traces = tuple(encode_variant(item, edge, order) for item in training_corpus())
        return infer_framing(traces)

    def test_rising_sampling_edge_is_inferred(self) -> None:
        result = self._infer(SamplingEdge.RISING, BitOrder.MSB_FIRST)

        self.assertEqual(result.sampling_edges, (SamplingEdge.RISING,))
        self.assertEqual(set(result.bit_orders), set(BitOrder))
        self.assertEqual(len(result.candidates), 2)

    def test_falling_sampling_edge_is_inferred(self) -> None:
        result = self._infer(SamplingEdge.FALLING, BitOrder.LSB_FIRST)

        self.assertEqual(result.sampling_edges, (SamplingEdge.FALLING,))
        self.assertEqual(set(result.bit_orders), set(BitOrder))
        self.assertEqual(len(result.candidates), 2)

    def test_wrong_edge_is_rejected_for_setup_violation(self) -> None:
        result = self._infer(SamplingEdge.RISING, BitOrder.MSB_FIRST)

        self.assertTrue(
            all(
                hypothesis.sampling_edge is SamplingEdge.FALLING
                and "sampling edge" in reason
                for hypothesis, reason in result.rejected
            )
        )

    def test_bit_order_ambiguity_preserves_equivalent_behavior(self) -> None:
        result = self._infer(SamplingEdge.RISING, BitOrder.MSB_FIRST)
        by_order = {
            candidate.hypothesis.bit_order: candidate for candidate in result.candidates
        }

        native = by_order[BitOrder.MSB_FIRST].model.emulate(HELD_OUT_REQUEST)
        reversed_model = by_order[BitOrder.LSB_FIRST].model.emulate(
            reverse_byte(HELD_OUT_REQUEST)
        )
        self.assertEqual(native, TimedResponse(0x67, 6))
        self.assertEqual(reversed_model, TimedResponse(reverse_byte(0x67), 6))

    def test_decoder_recovers_configured_convention(self) -> None:
        transaction = training_corpus()[3]
        for edge in SamplingEdge:
            for order in BitOrder:
                with self.subTest(edge=edge, order=order):
                    trace = encode_variant(transaction, edge, order)
                    hypothesis = FramingHypothesis(edge, order)
                    self.assertEqual(decode_with_hypothesis(trace, hypothesis), transaction)


if __name__ == "__main__":
    unittest.main()
