import unittest

from companion_controller import AsicSnapshot, DeckController, display_label
from companion_link import Command, ProductState, status_page


class DeckControllerTest(unittest.TestCase):
    def test_listen_discovers_then_learns_without_ownership(self) -> None:
        controller = DeckController()
        discovering = controller.command(
            AsicSnapshot(ProductState.OBSERVING),
            listen_pressed=True,
            jack_pressed=False,
            active_switch=False,
        )
        learning = controller.command(
            AsicSnapshot(ProductState.RESOLVED, normal_status=1),
            listen_pressed=True,
            jack_pressed=False,
            active_switch=False,
        )
        self.assertEqual(discovering, Command.REVOKE | Command.DISCOVER)
        self.assertEqual(learning, Command.REVOKE | Command.LEARN)
        self.assertFalse(discovering & Command.OWNERSHIP)
        self.assertFalse(learning & Command.OWNERSHIP)

    def test_jack_in_is_one_edge_for_each_admitted_action(self) -> None:
        for state, action in (
            (ProductState.PROBE_READY, Command.ACTIVATE),
            (ProductState.MODEL_READY, Command.ACTIVATE),
        ):
            with self.subTest(state=state):
                controller = DeckController()
                first = controller.command(
                    AsicSnapshot(state),
                    listen_pressed=False,
                    jack_pressed=True,
                    active_switch=True,
                )
                held = controller.command(
                    AsicSnapshot(state),
                    listen_pressed=False,
                    jack_pressed=True,
                    active_switch=True,
                )
                self.assertEqual(first, Command.OWNERSHIP | action)
                self.assertEqual(held, 0)

    def test_promotion_uses_explicit_capability_not_pretty_state(self) -> None:
        controller = DeckController()
        ready_status = (1 << 0) | (1 << 1) | (1 << 5)
        command = controller.command(
            AsicSnapshot(ProductState.AMBIGUOUS, ready_status),
            listen_pressed=False,
            jack_pressed=True,
            active_switch=True,
        )
        self.assertEqual(command, Command.OWNERSHIP | Command.PROMOTE)

    def test_active_work_holds_ownership_and_jack_in_revokes(self) -> None:
        controller = DeckController()
        for state in (ProductState.INTERROGATING, ProductState.EMULATING):
            with self.subTest(state=state):
                steady = controller.command(
                    AsicSnapshot(state),
                    listen_pressed=False,
                    jack_pressed=False,
                    active_switch=True,
                )
                abort = controller.command(
                    AsicSnapshot(state),
                    listen_pressed=False,
                    jack_pressed=True,
                    active_switch=True,
                )
                self.assertEqual(steady, Command.OWNERSHIP)
                self.assertEqual(abort, Command.REVOKE)
                controller.command(
                    AsicSnapshot(state),
                    listen_pressed=False,
                    jack_pressed=False,
                    active_switch=True,
                )

    def test_passive_switch_always_revokes(self) -> None:
        controller = DeckController()
        command = controller.command(
            AsicSnapshot(ProductState.EMULATING),
            listen_pressed=False,
            jack_pressed=False,
            active_switch=False,
        )
        self.assertEqual(command, Command.REVOKE)

    def test_listen_clears_fault_only_on_press_edge(self) -> None:
        controller = DeckController()
        snapshot = AsicSnapshot(ProductState.CONTENTION)
        first = controller.command(
            snapshot,
            listen_pressed=True,
            jack_pressed=False,
            active_switch=False,
        )
        held = controller.command(
            snapshot,
            listen_pressed=True,
            jack_pressed=False,
            active_switch=False,
        )
        self.assertEqual(first, Command.CLEAR_FAULT)
        self.assertEqual(held, Command.REVOKE | Command.DISCOVER)

    def test_polling_is_blocked_during_continuous_ownership(self) -> None:
        controller = DeckController()
        request = controller.poll_request(
            AsicSnapshot(ProductState.AMBIGUOUS), 3
        )
        self.assertEqual(status_page(request), (True, 3))
        for state in (ProductState.INTERROGATING, ProductState.EMULATING):
            with self.subTest(state=state):
                with self.assertRaisesRegex(RuntimeError, "ownership"):
                    controller.poll_request(AsicSnapshot(state), 3)

    def test_display_keeps_faults_literal(self) -> None:
        self.assertEqual(display_label(AsicSnapshot(ProductState.QUIET)), "SILENCE")
        self.assertEqual(
            display_label(AsicSnapshot(ProductState.CONTENTION)), "CONTENTION"
        )


if __name__ == "__main__":
    unittest.main()
