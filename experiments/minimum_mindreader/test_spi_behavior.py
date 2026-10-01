import unittest

from known_protocol_corpus import SPI_MISO, SPI_MOSI
from model import ReplayBaseline, TimedResponse, Transaction
from spi_behavior import (
    HELD_OUT_REQUEST,
    TRAINING_REQUESTS,
    infer_spi_behavior,
    lossy_response,
    make_spi_behavior_corpus,
    reversible_response,
)
from spi_hypothesis import SpiBitOrder


class SpiBehaviorTest(unittest.TestCase):
    def test_lossy_behavior_resolves_direction_for_every_spi_variant(self) -> None:
        for mode in range(4):
            for msb_first in (True, False):
                with self.subTest(mode=mode, msb_first=msb_first):
                    corpus = make_spi_behavior_corpus(mode, msb_first)
                    result = infer_spi_behavior(corpus)

                    self.assertEqual(result.waveform_count, len(TRAINING_REQUESTS))
                    self.assertEqual(result.physical_hypotheses_per_waveform, 384)
                    self.assertEqual(len(result.candidates), 2)
                    self.assertEqual(result.request_pins, (SPI_MOSI,))
                    self.assertEqual(result.response_pins, (SPI_MISO,))
                    self.assertEqual(set(result.bit_orders), set(SpiBitOrder))
                    self.assertTrue(
                        all(candidate.compile().encoded_bytes == 10 for candidate in result.candidates)
                    )

    def test_ground_truth_order_generalizes_to_held_out_transfer(self) -> None:
        corpus = make_spi_behavior_corpus(3, False)
        result = infer_spi_behavior(corpus)
        candidate = next(
            item
            for item in result.candidates
            if item.hypothesis.bit_order is SpiBitOrder.LSB_FIRST
        )

        self.assertEqual(
            candidate.compile().new_emulator().emulate(HELD_OUT_REQUEST),
            TimedResponse(lossy_response(HELD_OUT_REQUEST), 0),
        )

    def test_exact_replay_cannot_answer_held_out_transfer(self) -> None:
        replay = ReplayBaseline(
            Transaction(request, lossy_response(request), 0)
            for request in TRAINING_REQUESTS
        )

        self.assertIsNone(replay.emulate(HELD_OUT_REQUEST))

    def test_reversible_behavior_preserves_direction_symmetry(self) -> None:
        corpus = make_spi_behavior_corpus(
            0, True, response_function=reversible_response
        )
        result = infer_spi_behavior(corpus)

        self.assertEqual(len(result.candidates), 4)
        self.assertEqual(set(result.request_pins), {SPI_MOSI, SPI_MISO})
        self.assertEqual(set(result.response_pins), {SPI_MOSI, SPI_MISO})

    def test_one_transfer_is_insufficient_for_behavioral_direction(self) -> None:
        corpus = make_spi_behavior_corpus(0, True)[:1]

        self.assertEqual(infer_spi_behavior(corpus).candidates, ())


if __name__ == "__main__":
    unittest.main()
