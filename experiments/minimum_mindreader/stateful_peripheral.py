"""Synthetic two-state peripheral and training corpus for Experiment 002."""

from model import TimedResponse, Transaction


DATA_MASK = 0xF0
DATA_COMMAND = 0xA0
TOGGLE_COMMAND = 0xF0
TOGGLE_RESPONSE = TimedResponse(0x0F, 4)
DATA_DELAY_CYCLES = 6
TRAINING_PAYLOADS = (0x0, 0x1, 0x2, 0x4, 0x5, 0x8, 0xF)
HELD_OUT_REQUEST = 0xA7


class StatefulPeripheral:
    def __init__(self) -> None:
        self.state = 0

    def respond(self, request: int) -> TimedResponse | None:
        if request == TOGGLE_COMMAND:
            response = TOGGLE_RESPONSE
            self.state ^= 1
            return response
        if request & DATA_MASK == DATA_COMMAND:
            prefix = 0x60 if self.state == 0 else 0xE0
            return TimedResponse(prefix | (request & 0x0F), DATA_DELAY_CYCLES)
        return None


def observe_sequence(requests: tuple[int, ...]) -> tuple[Transaction, ...]:
    peripheral = StatefulPeripheral()
    observations: list[Transaction] = []
    for request in requests:
        response = peripheral.respond(request)
        if response is None:
            raise ValueError(f"unsupported stateful request: 0x{request:02X}")
        observations.append(Transaction(request, response.value, response.delay_cycles))
    return tuple(observations)


def _data_requests(reverse: bool = False) -> tuple[int, ...]:
    payloads = reversed(TRAINING_PAYLOADS) if reverse else TRAINING_PAYLOADS
    return tuple(DATA_COMMAND | payload for payload in payloads)


def training_sequences() -> tuple[tuple[Transaction, ...], ...]:
    forward = _data_requests()
    reverse = _data_requests(reverse=True)
    return (
        observe_sequence(forward + (TOGGLE_COMMAND,) + forward),
        observe_sequence(
            (TOGGLE_COMMAND,) + reverse + (TOGGLE_COMMAND,) + reverse
        ),
    )

