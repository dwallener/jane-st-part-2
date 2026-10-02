import unittest

from companion_link import Command, ProductState, status_page, status_request


class CompanionLinkTest(unittest.TestCase):
    def test_every_page_round_trips_in_both_banks(self) -> None:
        requests = set()
        for companion in (False, True):
            for page in range(32):
                request = status_request(page, companion=companion)
                self.assertEqual(status_page(request), (companion, page))
                self.assertFalse(request & Command.ACTIVATE)
                requests.add(request)
        self.assertEqual(len(requests), 64)

    def test_non_status_commands_are_rejected(self) -> None:
        for request in (0, int(Command.ACTIVATE), 0x90):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    status_page(request)

    def test_product_state_codes_do_not_overlap_fault_range(self) -> None:
        ordinary = tuple(state for state in ProductState if state.value < 0xE0)
        faults = tuple(state for state in ProductState if state.value >= 0xE0)
        self.assertEqual(len(ordinary), 9)
        self.assertEqual(len(faults), 5)


if __name__ == "__main__":
    unittest.main()
