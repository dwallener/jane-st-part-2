"""Reference product policy for The Deck companion MCU."""

from __future__ import annotations

from dataclasses import dataclass

from companion_link import Command, ProductState, status_request


FAULT_STATES = frozenset(
    {
        ProductState.COMPROMISED,
        ProductState.CONTRADICTION,
        ProductState.CONTENTION,
        ProductState.TIMEOUT,
        ProductState.REVOKED,
    }
)
OWNERSHIP_STATES = frozenset(
    {ProductState.INTERROGATING, ProductState.EMULATING}
)


@dataclass(frozen=True)
class AsicSnapshot:
    state: ProductState
    normal_status: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.normal_status <= 0xFF:
            raise ValueError("normal status must be a byte")

    @property
    def physical_complete(self) -> bool:
        return bool(self.normal_status & (1 << 0))

    @property
    def fault(self) -> bool:
        return self.state in FAULT_STATES

    @property
    def promotion_ready(self) -> bool:
        required = (1 << 0) | (1 << 1) | (1 << 5)
        forbidden = (1 << 2) | (1 << 6)
        return (self.normal_status & required) == required and not (
            self.normal_status & forbidden
        )

    @property
    def requires_continuous_ownership(self) -> bool:
        return self.state in OWNERSHIP_STATES


class DeckController:
    """Turn physical controls and ASIC state into one ui[7:0] command byte."""

    def __init__(self) -> None:
        self._listen_previous = False
        self._jack_previous = False

    def command(
        self,
        snapshot: AsicSnapshot,
        *,
        listen_pressed: bool,
        jack_pressed: bool,
        active_switch: bool,
    ) -> int:
        listen_rise = listen_pressed and not self._listen_previous
        jack_rise = jack_pressed and not self._jack_previous
        self._listen_previous = listen_pressed
        self._jack_previous = jack_pressed

        if snapshot.fault and listen_rise:
            return int(Command.CLEAR_FAULT)

        if not active_switch:
            command = Command.REVOKE
            if listen_pressed:
                command |= (
                    Command.LEARN
                    if snapshot.physical_complete
                    else Command.DISCOVER
                )
            return int(command)

        if snapshot.fault:
            return int(Command.REVOKE)

        if snapshot.requires_continuous_ownership:
            return int(Command.REVOKE if jack_rise else Command.OWNERSHIP)

        if listen_pressed:
            return int(
                Command.LEARN
                if snapshot.physical_complete
                else Command.DISCOVER
            )

        if jack_rise:
            if snapshot.promotion_ready:
                return int(Command.OWNERSHIP | Command.PROMOTE)
            if snapshot.state in {
                ProductState.PROBE_READY,
                ProductState.MODEL_READY,
            }:
                return int(Command.OWNERSHIP | Command.ACTIVATE)

        return 0

    @staticmethod
    def poll_request(snapshot: AsicSnapshot, page: int) -> int:
        if snapshot.requires_continuous_ownership:
            raise RuntimeError("paged reads would remove continuous ownership")
        return status_request(page, companion=True)


DISPLAY_LABEL = {
    ProductState.RESET: "BOOT",
    ProductState.OBSERVING: "LISTENING",
    ProductState.QUIET: "SILENCE",
    ProductState.AMBIGUOUS: "FORK",
    ProductState.PROBE_READY: "QUESTION READY",
    ProductState.INTERROGATING: "ASKING",
    ProductState.RESOLVED: "LOCK",
    ProductState.MODEL_READY: "GHOST READY",
    ProductState.EMULATING: "GHOSTING",
    ProductState.COMPROMISED: "EVIDENCE LOST",
    ProductState.CONTRADICTION: "CONTRADICTION",
    ProductState.CONTENTION: "CONTENTION",
    ProductState.TIMEOUT: "TIMEOUT",
    ProductState.REVOKED: "REVOKED",
}


def display_label(snapshot: AsicSnapshot) -> str:
    return DISPLAY_LABEL[snapshot.state]
