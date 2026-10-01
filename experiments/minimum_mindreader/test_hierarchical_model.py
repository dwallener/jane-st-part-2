import unittest

from hierarchical_model import HierarchicalSpiModel, build_hierarchical_spi_model
from known_protocol_corpus import SPI_CLOCK, SPI_MISO, SPI_MOSI, SPI_SELECT_N, make_spi_case
from model import TimedResponse
from spi_behavior import (
    HELD_OUT_REQUEST,
    lossy_response,
    make_spi_behavior_corpus,
    reversible_response,
)
from spi_hypothesis import SpiSamplingEdge, decode_spi_hypothesis


class HierarchicalModelTest(unittest.TestCase):
    def test_all_spi_variants_serialize_to_twenty_two_bytes(self) -> None:
        for mode in range(4):
            for msb_first in (True, False):
                with self.subTest(mode=mode, msb_first=msb_first):
                    artifact = build_hierarchical_spi_model(
                        make_spi_behavior_corpus(mode, msb_first)
                    )
                    encoded = artifact.encode()

                    self.assertEqual(len(encoded), 22)
                    self.assertEqual(artifact.storage_bits, 176)
                    self.assertEqual(HierarchicalSpiModel.decode(encoded), artifact)
                    self.assertEqual(artifact.program.encoded_bytes, 10)

    def test_artifact_contains_resolved_physical_roles_and_provenance(self) -> None:
        artifact = build_hierarchical_spi_model(make_spi_behavior_corpus(3, False))

        self.assertEqual(artifact.physical.select_pin, SPI_SELECT_N)
        self.assertEqual(artifact.physical.clock_pin, SPI_CLOCK)
        self.assertEqual(artifact.physical.request_pin, SPI_MOSI)
        self.assertEqual(artifact.physical.response_pin, SPI_MISO)
        self.assertEqual(artifact.physical.select_active_level, 0)
        self.assertEqual(artifact.physical.clock_idle_level, 1)
        self.assertEqual(artifact.physical.sampling_edge, SpiSamplingEdge.TRAILING)
        self.assertTrue(artifact.bit_reverse_equivalent)
        self.assertEqual(artifact.provenance.waveform_count, 8)
        self.assertEqual(artifact.provenance.physical_evaluations, 3072)
        self.assertEqual(artifact.provenance.equivalent_survivors, 2)

    def test_canonical_model_matches_held_out_wire_response(self) -> None:
        artifact = build_hierarchical_spi_model(make_spi_behavior_corpus(3, False))
        held_out = make_spi_case(
            3,
            False,
            request=HELD_OUT_REQUEST,
            response=lossy_response(HELD_OUT_REQUEST),
        )
        decoded_request, decoded_response = decode_spi_hypothesis(
            held_out.inference_input(),
            artifact.physical.canonical_hypothesis(),
        )

        self.assertEqual(
            artifact.emulate_decoded(decoded_request),
            TimedResponse(decoded_response, 0),
        )

    def test_reversible_direction_cannot_be_canonicalized_away(self) -> None:
        corpus = make_spi_behavior_corpus(
            0, True, response_function=reversible_response
        )

        with self.assertRaisesRegex(ValueError, "direction resolved"):
            build_hierarchical_spi_model(corpus)

    def test_corrupt_or_truncated_artifact_is_rejected(self) -> None:
        encoded = bytearray(
            build_hierarchical_spi_model(make_spi_behavior_corpus(0, True)).encode()
        )
        encoded[0] ^= 0x01
        with self.assertRaisesRegex(ValueError, "magic"):
            HierarchicalSpiModel.decode(bytes(encoded))

        valid = build_hierarchical_spi_model(
            make_spi_behavior_corpus(0, True)
        ).encode()
        with self.assertRaisesRegex(ValueError, "length"):
            HierarchicalSpiModel.decode(valid[:-1])


if __name__ == "__main__":
    unittest.main()
