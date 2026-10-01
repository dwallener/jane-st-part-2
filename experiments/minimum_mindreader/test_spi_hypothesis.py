import unittest

from known_protocol_corpus import benchmark_cases
from spi_hypothesis import SpiBitOrder, SpiSamplingEdge, infer_spi


def reverse_byte(value: int) -> int:
    return int(f"{value:08b}"[::-1], 2)


class SpiHypothesisTest(unittest.TestCase):
    def test_all_canonical_spi_variants_recover_physical_timing(self) -> None:
        cases = [case for case in benchmark_cases() if case.truth.family == "SPI"]

        for case in cases:
            with self.subTest(case=case.name):
                result = infer_spi(case.inference_input())
                mode = int(case.truth.parameter("mode"))
                expected_edge = (
                    SpiSamplingEdge.TRAILING
                    if mode & 1
                    else SpiSamplingEdge.LEADING
                )

                self.assertEqual(result.hypothesis_count, 384)
                self.assertEqual(result.select_pins, (case.truth.pin("select_n"),))
                self.assertEqual(result.clock_pins, (case.truth.pin("clock"),))
                self.assertEqual(result.select_active_levels, (0,))
                self.assertEqual(result.clock_idle_levels, (mode >> 1,))
                self.assertEqual(result.sampling_edges, (expected_edge,))
                self.assertEqual(set(result.bit_orders), set(SpiBitOrder))
                self.assertEqual(
                    result.unordered_data_pin_pairs,
                    (
                        frozenset(
                            (
                                case.truth.pin("request_data"),
                                case.truth.pin("response_data"),
                            )
                        ),
                    ),
                )
                self.assertEqual(len(result.candidates), 4)

    def test_survivors_differ_only_by_data_labels_and_bit_order(self) -> None:
        case = next(case for case in benchmark_cases() if case.name == "spi_mode3_lsb_first")
        result = infer_spi(case.inference_input())
        request = case.truth.expected_input_symbols[0]
        response = case.truth.expected_output_symbols[0]

        observed_pairs = {
            (candidate.data_a_word, candidate.data_b_word)
            for candidate in result.candidates
        }
        expected_pairs = {
            (request, response),
            (response, request),
            (reverse_byte(request), reverse_byte(response)),
            (reverse_byte(response), reverse_byte(request)),
        }
        self.assertEqual(observed_pairs, expected_pairs)

    def test_non_four_pin_waveform_is_explicitly_unsupported(self) -> None:
        uart = next(case for case in benchmark_cases() if case.truth.family == "UART")

        with self.assertRaisesRegex(ValueError, "exactly four pins"):
            infer_spi(uart.inference_input())


if __name__ == "__main__":
    unittest.main()
