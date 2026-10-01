import unittest

from model import BitExpression, ExpressionKind, TimedResponse, learn
from protocol_program import (
    GuardedTransition,
    ProtocolProgram,
    compile_stateless,
    compile_toggle,
)
from state_model import learn_toggle_machine
from stateful_peripheral import TOGGLE_COMMAND, training_sequences
from synthetic_peripheral import HELD_OUT_REQUEST, training_corpus


class ProtocolProgramTest(unittest.TestCase):
    def test_stateless_model_compiles_to_ten_bytes(self) -> None:
        program = compile_stateless(learn(training_corpus()))
        emulator = program.new_emulator()

        self.assertEqual(program.encoded_bytes, 10)
        self.assertEqual(emulator.emulate(HELD_OUT_REQUEST), TimedResponse(0x67, 6))
        self.assertIsNone(emulator.emulate(0xB7))

    def test_two_state_model_compiles_to_one_interpreter(self) -> None:
        learned = learn_toggle_machine(training_sequences()).model
        assert learned is not None
        program = compile_toggle(learned)
        emulator = program.new_emulator()

        self.assertEqual(program.encoded_bytes, 40)
        self.assertEqual(emulator.emulate(0xA7), TimedResponse(0x67, 6))
        self.assertEqual(emulator.emulate(TOGGLE_COMMAND), TimedResponse(0x0F, 4))
        self.assertEqual(emulator.emulate(0xA7), TimedResponse(0xE7, 6))
        self.assertIsNone(emulator.emulate(0xB7))
        self.assertEqual(emulator.state, 1, "unknown requests must not change state")

    def test_encoding_round_trip_preserves_behavior(self) -> None:
        learned = learn_toggle_machine(training_sequences()).model
        assert learned is not None
        original = compile_toggle(learned)
        decoded = ProtocolProgram.decode(original.encode())
        original_emulator = original.new_emulator()
        decoded_emulator = decoded.new_emulator()

        requests = (0xA7, TOGGLE_COMMAND, 0xA2, TOGGLE_COMMAND, 0xAF)
        self.assertEqual(
            [original_emulator.emulate(request) for request in requests],
            [decoded_emulator.emulate(request) for request in requests],
        )

    def test_overlapping_guards_are_rejected(self) -> None:
        constant_zero = tuple(
            BitExpression(ExpressionKind.CONSTANT, 0) for _ in range(8)
        )
        broad = GuardedTransition(0, 0xF0, 0xA0, constant_zero, 1, 0)
        overlapping = GuardedTransition(0, 0xFF, 0xA7, constant_zero, 1, 0)

        with self.assertRaisesRegex(ValueError, "overlapping request guards"):
            ProtocolProgram((broad, overlapping))

    def test_invalid_expression_encoding_is_rejected(self) -> None:
        program = bytearray(compile_stateless(learn(training_corpus())).encode())
        program[3] = (program[3] & 0xE0) | 0x1F

        with self.assertRaisesRegex(ValueError, "invalid response expression"):
            ProtocolProgram.decode(bytes(program))


if __name__ == "__main__":
    unittest.main()
