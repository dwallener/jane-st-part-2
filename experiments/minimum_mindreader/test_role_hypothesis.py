import unittest

from framing_hypothesis import PinRoles
from role_hypothesis import infer_pin_roles
from synthetic_link import CLOCK, REQUEST_DATA, RESPONSE_DATA, RESPONSE_VALID, SELECT
from synthetic_peripheral import training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant, remap_pins


class RoleHypothesisTest(unittest.TestCase):
    def _traces(self, roles: PinRoles, edge: SamplingEdge, order: BitOrder):
        return tuple(
            remap_pins(
                encode_variant(item, edge, order),
                input_mapping={
                    CLOCK: roles.clock,
                    REQUEST_DATA: roles.request_data,
                    SELECT: roles.select,
                },
                output_mapping={
                    RESPONSE_DATA: roles.response_data,
                    RESPONSE_VALID: roles.response_valid,
                },
            )
            for item in training_corpus()
        )

    def test_default_roles_are_recovered(self) -> None:
        expected = PinRoles()
        result = infer_pin_roles(
            self._traces(expected, SamplingEdge.RISING, BitOrder.MSB_FIRST)
        )

        self.assertEqual(result.hypothesis_count, 48)
        self.assertEqual(result.role_assignments, (expected,))
        self.assertEqual(result.sampling_edges, (SamplingEdge.RISING,))
        self.assertEqual(set(result.bit_orders), set(BitOrder))
        self.assertEqual(len(result.candidates), 2)

    def test_permuted_roles_are_recovered(self) -> None:
        expected = PinRoles(
            clock=0x04,
            request_data=0x01,
            select=0x02,
            response_data=0x02,
            response_valid=0x01,
        )
        result = infer_pin_roles(
            self._traces(expected, SamplingEdge.FALLING, BitOrder.LSB_FIRST)
        )

        self.assertEqual(result.role_assignments, (expected,))
        self.assertEqual(result.sampling_edges, (SamplingEdge.FALLING,))
        self.assertEqual(set(result.bit_orders), set(BitOrder))
        self.assertEqual(len(result.candidates), 2)

    def test_search_requires_complete_behavioral_model(self) -> None:
        expected = PinRoles()
        one_trace = self._traces(
            expected, SamplingEdge.RISING, BitOrder.MSB_FIRST
        )[:1]

        self.assertEqual(infer_pin_roles(one_trace).candidates, ())

    def test_pin_remap_rejects_aliases(self) -> None:
        trace = encode_variant(
            training_corpus()[0], SamplingEdge.RISING, BitOrder.MSB_FIRST
        )

        with self.assertRaisesRegex(ValueError, "destinations must be unique"):
            remap_pins(
                trace,
                input_mapping={CLOCK: 0x01, REQUEST_DATA: 0x01, SELECT: 0x04},
                output_mapping={RESPONSE_DATA: 0x01, RESPONSE_VALID: 0x02},
            )


if __name__ == "__main__":
    unittest.main()
