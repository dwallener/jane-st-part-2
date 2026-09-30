import unittest

from edge_trace import strip_markers
from model import ReplayBaseline, TimedResponse, Transaction
from state_model import learn_toggle_machine
from stateful_peripheral import (
    DATA_DELAY_CYCLES,
    HELD_OUT_REQUEST,
    TOGGLE_COMMAND,
    TOGGLE_RESPONSE,
    training_sequences,
)
from synthetic_link import encode_transaction, infer_transaction


class StatefulLearningTest(unittest.TestCase):
    def test_infers_unique_toggle_request(self) -> None:
        result = learn_toggle_machine(training_sequences())

        self.assertTrue(result.is_complete)
        self.assertEqual(result.candidate_requests, (TOGGLE_COMMAND,))

    def test_held_out_request_generalizes_in_both_states(self) -> None:
        model = learn_toggle_machine(training_sequences()).model
        assert model is not None
        emulator = model.new_emulator()

        self.assertEqual(
            emulator.emulate(HELD_OUT_REQUEST),
            TimedResponse(0x67, DATA_DELAY_CYCLES),
        )
        self.assertEqual(emulator.emulate(TOGGLE_COMMAND), TOGGLE_RESPONSE)
        self.assertEqual(
            emulator.emulate(HELD_OUT_REQUEST),
            TimedResponse(0xE7, DATA_DELAY_CYCLES),
        )
        self.assertEqual(emulator.emulate(TOGGLE_COMMAND), TOGGLE_RESPONSE)
        self.assertEqual(
            emulator.emulate(HELD_OUT_REQUEST),
            TimedResponse(0x67, DATA_DELAY_CYCLES),
        )

    def test_identical_request_depends_on_history(self) -> None:
        model = learn_toggle_machine(training_sequences()).model
        assert model is not None
        emulator = model.new_emulator()

        self.assertEqual(emulator.emulate(0xA5), TimedResponse(0x65, 6))
        emulator.emulate(TOGGLE_COMMAND)
        self.assertEqual(emulator.emulate(0xA5), TimedResponse(0xE5, 6))

    def test_stateless_replay_cannot_represent_corpus(self) -> None:
        flattened = (
            item for sequence in training_sequences() for item in sequence
        )

        with self.assertRaisesRegex(ValueError, "conflicting replay"):
            ReplayBaseline(flattened)

    def test_markerless_traces_preserve_state_learning(self) -> None:
        recovered = tuple(
            tuple(
                infer_transaction(strip_markers(encode_transaction(item)))
                for item in sequence
            )
            for sequence in training_sequences()
        )

        result = learn_toggle_machine(recovered)
        self.assertEqual(result.candidate_requests, (TOGGLE_COMMAND,))

    def test_insufficient_state_evidence_remains_ambiguous(self) -> None:
        state_zero_only = (training_sequences()[0][:4],)

        self.assertFalse(learn_toggle_machine(state_zero_only).is_complete)

    def test_conflicting_control_response_eliminates_candidate(self) -> None:
        sequences = [list(sequence) for sequence in training_sequences()]
        for index, item in enumerate(sequences[1]):
            if item.request == TOGGLE_COMMAND:
                sequences[1][index] = Transaction(
                    item.request,
                    item.response ^ 0x01,
                    item.delay_cycles,
                )
                break

        result = learn_toggle_machine(sequences)
        self.assertNotIn(TOGGLE_COMMAND, result.candidate_requests)


if __name__ == "__main__":
    unittest.main()

