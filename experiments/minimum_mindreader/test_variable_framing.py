import unittest

from variable_framing import (
    DelimiterFraming,
    FramingKind,
    LengthFraming,
    learn_variable_framing,
)


LENGTH_TRAINING = (
    (0x02, 0x10, 0x11),
    (0x04, 0x20, 0x21, 0x22, 0x23),
    (0x01, 0x30),
)
DELIMITER_TRAINING = (
    (0x10, 0x11, 0x7E),
    (0x20, 0x21, 0x22, 0x7E),
    (0x30, 0x7E),
)
AMBIGUOUS_TRAINING = (
    (0x02, 0x41, 0x7E),
    (0x03, 0x42, 0x43, 0x7E),
)


class VariableFramingTest(unittest.TestCase):
    def test_infers_length_field_and_segments_held_out_stream(self) -> None:
        result = learn_variable_framing(LENGTH_TRAINING)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.model, LengthFraming(0, 1, 64))
        assert result.model is not None
        self.assertEqual(
            result.model.parse((0x03, 0xAA, 0xBB, 0xCC, 0x01, 0xDD)),
            ((0x03, 0xAA, 0xBB, 0xCC), (0x01, 0xDD)),
        )

    def test_infers_delimiter_and_segments_held_out_stream(self) -> None:
        result = learn_variable_framing(DELIMITER_TRAINING)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.model, DelimiterFraming(0x7E, 64))
        assert result.model is not None
        self.assertEqual(
            result.model.parse((0x44, 0x45, 0x7E, 0x55, 0x7E)),
            ((0x44, 0x45, 0x7E), (0x55, 0x7E)),
        )

    def test_ambiguous_training_retains_both_explanations(self) -> None:
        result = learn_variable_framing(AMBIGUOUS_TRAINING)

        self.assertFalse(result.is_complete)
        self.assertEqual(result.kinds, (FramingKind.LENGTH, FramingKind.DELIMITER))

    def test_additional_evidence_can_select_length(self) -> None:
        result = learn_variable_framing(AMBIGUOUS_TRAINING + ((0x01, 0x44),))

        self.assertTrue(result.is_complete)
        self.assertEqual(result.kinds, (FramingKind.LENGTH,))

    def test_additional_evidence_can_select_delimiter(self) -> None:
        result = learn_variable_framing(
            AMBIGUOUS_TRAINING + ((0x50, 0x51, 0x7E),)
        )

        self.assertTrue(result.is_complete)
        self.assertEqual(result.kinds, (FramingKind.DELIMITER,))

    def test_incomplete_held_out_stream_is_rejected(self) -> None:
        length = learn_variable_framing(LENGTH_TRAINING).model
        delimiter = learn_variable_framing(DELIMITER_TRAINING).model
        assert length is not None and delimiter is not None

        with self.assertRaisesRegex(ValueError, "inside a length-prefixed frame"):
            length.parse((0x03, 0xAA))
        with self.assertRaisesRegex(ValueError, "before a delimiter"):
            delimiter.parse((0x44, 0x45))

    def test_unescaped_interior_delimiter_is_not_silently_accepted(self) -> None:
        frames = ((0x10, 0x7E, 0x20, 0x7E), (0x30, 0x7E))

        result = learn_variable_framing(frames)

        self.assertNotIn(FramingKind.DELIMITER, result.kinds)


if __name__ == "__main__":
    unittest.main()
