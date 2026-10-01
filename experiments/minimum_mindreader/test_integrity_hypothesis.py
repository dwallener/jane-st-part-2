import unittest

from integrity_hypothesis import (
    CRC8_CATALOG,
    ConstantTrailer,
    IntegrityKind,
    NegativeSum8,
    Sum8,
    Xor8,
    frame_with_integrity,
    infer_integrity,
    validate_frame,
)


PAYLOADS = (
    (0x01, 0x02, 0x03),
    (0x10, 0x20),
    (0xFF, 0x00, 0x55, 0xAA),
    (0x31, 0x32, 0x33, 0x34),
)


class IntegrityHypothesisTest(unittest.TestCase):
    def _infer_generated(self, model):
        frames = tuple(frame_with_integrity(payload, model) for payload in PAYLOADS)
        return infer_integrity(frames)

    def test_known_crc_check_vectors(self) -> None:
        payload = tuple(b"123456789")
        expected = {
            "CRC-8/SMBUS": 0xF4,
            "CRC-8/SAE-J1850": 0x4B,
            "CRC-8/MAXIM-DOW": 0xA1,
            "CRC-8/ROHC": 0xD0,
        }

        self.assertEqual(
            {model.name: model.compute(payload) for model in CRC8_CATALOG},
            expected,
        )

    def test_xor_sum_and_negative_sum_are_identified(self) -> None:
        for model in (Xor8(), Sum8(), NegativeSum8()):
            with self.subTest(model=model):
                result = self._infer_generated(model)
                self.assertTrue(result.is_complete)
                self.assertEqual(result.model, model)

    def test_each_catalog_crc_is_identified(self) -> None:
        for model in CRC8_CATALOG:
            with self.subTest(model=model.name):
                result = self._infer_generated(model)
                self.assertTrue(result.is_complete)
                self.assertEqual(result.model, model)

    def test_constant_trailer_is_a_negative_control(self) -> None:
        result = self._infer_generated(ConstantTrailer(0xA5))

        self.assertTrue(result.is_complete)
        self.assertEqual(result.model, ConstantTrailer(0xA5))

    def test_ambiguous_constant_and_xor_rules_are_retained(self) -> None:
        frames = (
            (0x10, 0x20, 0x30),
            (0x11, 0x21, 0x30),
        )

        result = infer_integrity(frames)

        self.assertFalse(result.is_complete)
        self.assertIn(IntegrityKind.CONSTANT, result.kinds)
        self.assertIn(IntegrityKind.XOR8, result.kinds)
        probe = result.propose_probe()
        self.assertIsNotNone(probe)
        assert probe is not None
        self.assertGreater(len(set(probe.predicted_trailers)), 1)

    def test_additional_frame_resolves_ambiguous_rules(self) -> None:
        frames = (
            (0x10, 0x20, 0x30),
            (0x11, 0x21, 0x30),
            frame_with_integrity((0x12, 0x20), Xor8()),
        )

        result = infer_integrity(frames)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.model, Xor8())

    def test_held_out_corruption_is_detected(self) -> None:
        model = CRC8_CATALOG[0]
        frame = frame_with_integrity((0xDE, 0xAD, 0xBE, 0xEF), model)
        corrupted = (frame[0] ^ 0x01,) + frame[1:]

        self.assertTrue(validate_frame(frame, model))
        self.assertFalse(validate_frame(corrupted, model))


if __name__ == "__main__":
    unittest.main()
