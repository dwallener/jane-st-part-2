import unittest

from model import ReplayBaseline, TimedResponse, Transaction, learn
from synthetic_peripheral import (
    HELD_OUT_REQUEST,
    RESPONSE_DELAY_CYCLES,
    training_corpus,
)


class MinimumMindreaderTest(unittest.TestCase):
    def test_generalizes_to_held_out_request(self) -> None:
        model = learn(training_corpus())

        self.assertTrue(model.is_complete)
        self.assertEqual(model.request_mask, 0xF0)
        self.assertEqual(model.request_value, 0xA0)
        self.assertEqual(
            model.emulate(HELD_OUT_REQUEST),
            TimedResponse(value=0x67, delay_cycles=RESPONSE_DELAY_CYCLES),
        )

    def test_replay_cannot_answer_held_out_request(self) -> None:
        replay = ReplayBaseline(training_corpus())

        self.assertIsNone(replay.emulate(HELD_OUT_REQUEST))

    def test_rejects_request_outside_learned_family(self) -> None:
        model = learn(training_corpus())

        self.assertIsNone(model.emulate(0xB7))

    def test_ambiguous_evidence_remains_unknown(self) -> None:
        ambiguous = (
            Transaction(0xA0, 0x60, RESPONSE_DELAY_CYCLES),
            Transaction(0xAF, 0x6F, RESPONSE_DELAY_CYCLES),
        )
        model = learn(ambiguous)

        self.assertFalse(model.is_complete)
        self.assertIsNone(model.emulate(HELD_OUT_REQUEST))

    def test_conflicting_delays_remain_unknown(self) -> None:
        corpus = list(training_corpus())
        last = corpus[-1]
        corpus[-1] = Transaction(last.request, last.response, last.delay_cycles + 1)
        model = learn(corpus)

        self.assertIsNone(model.delay_cycles)
        self.assertFalse(model.is_complete)
        self.assertIsNone(model.emulate(HELD_OUT_REQUEST))


if __name__ == "__main__":
    unittest.main()
