import unittest

from edge_trace import Marker, Trace, TraceEvent, strip_markers
from model import ReplayBaseline, TimedResponse, Transaction, learn
from synthetic_link import (
    RESPONSE_VALID,
    decode_transaction,
    encode_transaction,
    infer_transaction,
)
from synthetic_peripheral import (
    HELD_OUT_REQUEST,
    RESPONSE_DELAY_CYCLES,
    training_corpus,
)


class EdgeTraceTest(unittest.TestCase):
    def test_codec_recovers_training_transactions(self) -> None:
        corpus = training_corpus()
        recovered = tuple(
            decode_transaction(encode_transaction(transaction))
            for transaction in corpus
        )

        self.assertEqual(recovered, corpus)

    def test_trace_learner_generalizes_but_replay_does_not(self) -> None:
        recovered = tuple(
            decode_transaction(encode_transaction(transaction))
            for transaction in training_corpus()
        )

        replay = ReplayBaseline(recovered)
        model = learn(recovered)

        self.assertIsNone(replay.emulate(HELD_OUT_REQUEST))
        self.assertEqual(
            model.emulate(HELD_OUT_REQUEST),
            TimedResponse(0x67, RESPONSE_DELAY_CYCLES),
        )
        self.assertIsNone(model.emulate(0xB7))

    def test_csv_round_trip_is_lossless(self) -> None:
        trace = encode_transaction(training_corpus()[0])

        self.assertEqual(Trace.from_csv(trace.to_csv()), trace)

    def test_markerless_framing_recovers_training_transactions(self) -> None:
        corpus = training_corpus()
        recovered = tuple(
            infer_transaction(strip_markers(encode_transaction(transaction)))
            for transaction in corpus
        )

        self.assertEqual(recovered, corpus)
        self.assertTrue(
            all(event.marker is None for event in strip_markers(encode_transaction(corpus[0])).events)
        )

    def test_markerless_trace_preserves_held_out_result(self) -> None:
        recovered = tuple(
            infer_transaction(strip_markers(encode_transaction(transaction)))
            for transaction in training_corpus()
        )

        self.assertEqual(
            learn(recovered).emulate(HELD_OUT_REQUEST),
            TimedResponse(0x67, RESPONSE_DELAY_CYCLES),
        )

    def test_markerless_decoder_recovers_variable_delay(self) -> None:
        transaction = Transaction(0xA5, 0x65, 11)

        self.assertEqual(
            infer_transaction(strip_markers(encode_transaction(transaction))),
            transaction,
        )

    def test_unobservable_response_start_is_rejected(self) -> None:
        trace = strip_markers(encode_transaction(training_corpus()[0]))
        previous_output = 0
        events = []
        carried_cycles = 0
        for event in trace.events:
            output_value = event.output_value & ~RESPONSE_VALID
            output_changed = previous_output ^ output_value
            delta_cycles = event.delta_cycles + carried_cycles
            carried_cycles = 0
            if event.input_changed == 0 and output_changed == 0:
                carried_cycles = delta_cycles
                continue
            events.append(
                TraceEvent(
                    delta_cycles=delta_cycles,
                    input_value=event.input_value,
                    input_changed=event.input_changed,
                    output_value=output_value,
                    output_changed=output_changed,
                )
            )
            previous_output = output_value

        with self.assertRaisesRegex(ValueError, "unobservable"):
            infer_transaction(Trace(tuple(events)))

    def test_changed_masks_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "input_changed"):
            Trace(
                (
                    TraceEvent(
                        delta_cycles=1,
                        input_value=0x01,
                        input_changed=0x00,
                        output_value=0,
                        output_changed=0,
                        marker=Marker.REQUEST_START,
                    ),
                )
            )

    def test_missing_boundary_marker_is_rejected(self) -> None:
        trace = encode_transaction(training_corpus()[0])
        events = tuple(
            event for event in trace.events if event.marker is not Marker.REQUEST_END
        )

        with self.assertRaisesRegex(ValueError, "marker order"):
            decode_transaction(Trace(events))


if __name__ == "__main__":
    unittest.main()
