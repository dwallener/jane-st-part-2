import unittest

from known_protocol_corpus import DigitalWaveform, benchmark_cases
from waveform_adapter import (
    AnonymousEdgeEvent,
    AnonymousEdgeTrace,
    compress_waveform,
    expand_edge_trace,
    profile_pins,
    score_current_frontend,
)


class WaveformAdapterTest(unittest.TestCase):
    def test_every_known_waveform_round_trips_losslessly(self) -> None:
        for case in benchmark_cases():
            with self.subTest(case=case.name):
                compressed = compress_waveform(case.inference_input())
                self.assertEqual(expand_edge_trace(compressed), case.inference_input())
                self.assertEqual(
                    compressed.duration_cycles,
                    len(case.waveform.samples) - 1,
                )

    def test_trailing_idle_time_is_preserved(self) -> None:
        waveform = DigitalWaveform(1, (0, 1, 1, 1, 1))

        compressed = compress_waveform(waveform)

        self.assertEqual(compressed.trailing_cycles, 3)
        self.assertEqual(expand_edge_trace(compressed), waveform)

    def test_changed_masks_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "changed mask"):
            AnonymousEdgeTrace(
                pin_count=2,
                initial_value=0,
                events=(AnonymousEdgeEvent(1, 1, 2),),
                trailing_cycles=0,
            )

    def test_spi_clock_has_sixteen_transitions(self) -> None:
        case = next(case for case in benchmark_cases() if case.name == "spi_mode0_msb_first")
        activities = profile_pins(compress_waveform(case.waveform))
        clock = case.truth.pin("clock")

        self.assertEqual(activities[clock].transition_count, 16)
        self.assertEqual(activities[clock].rising_edges, 8)
        self.assertEqual(activities[clock].falling_edges, 8)

    def test_known_families_reach_their_symbol_frontends(self) -> None:
        scores = tuple(score_current_frontend(case) for case in benchmark_cases())

        self.assertEqual(len(scores), 13)
        self.assertEqual(
            sum(score.deepest_passed_layer == "spi_symbols" for score in scores),
            8,
        )
        self.assertEqual(
            sum(score.deepest_passed_layer == "uart_symbols" for score in scores),
            4,
        )
        self.assertEqual(
            sum(score.deepest_passed_layer == "i2c_frames" for score in scores),
            1,
        )


if __name__ == "__main__":
    unittest.main()
