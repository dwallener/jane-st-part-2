import unittest

from known_protocol_corpus import (
    DigitalWaveform,
    benchmark_cases,
    decode_i2c_reference,
    decode_spi_reference,
    decode_uart_reference,
)


class KnownProtocolCorpusTest(unittest.TestCase):
    def test_initial_corpus_has_expected_coverage(self) -> None:
        cases = benchmark_cases()

        self.assertEqual(len(cases), 13)
        self.assertEqual({case.truth.family for case in cases}, {"SPI", "UART", "I2C"})
        self.assertEqual(len({case.name for case in cases}), len(cases))

    def test_all_spi_modes_and_orders_round_trip(self) -> None:
        cases = [case for case in benchmark_cases() if case.truth.family == "SPI"]

        self.assertEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case.name):
                request, response = decode_spi_reference(case)
                self.assertEqual((request,), case.truth.expected_input_symbols)
                self.assertEqual((response,), case.truth.expected_output_symbols)

    def test_uart_8n1_vectors_round_trip(self) -> None:
        cases = [case for case in benchmark_cases() if case.truth.family == "UART"]

        self.assertEqual(len(cases), 4)
        for case in cases:
            with self.subTest(case=case.name):
                self.assertEqual(
                    (decode_uart_reference(case),),
                    case.truth.expected_input_symbols,
                )

    def test_i2c_start_ack_and_stop_vector_round_trips(self) -> None:
        case = next(case for case in benchmark_cases() if case.truth.family == "I2C")

        symbols, acknowledgements = decode_i2c_reference(case)

        self.assertEqual(symbols, case.truth.expected_input_symbols)
        self.assertEqual(acknowledgements, case.truth.expected_ack_bits)

    def test_inference_view_does_not_expose_protocol_labels(self) -> None:
        for case in benchmark_cases():
            evidence = case.inference_input()
            self.assertIsInstance(evidence, DigitalWaveform)
            self.assertFalse(hasattr(evidence, "family"))
            self.assertFalse(hasattr(evidence, "pin_roles"))
            self.assertFalse(hasattr(evidence, "parameters"))


if __name__ == "__main__":
    unittest.main()
