"""Synthetic unknown peripheral used by CLAIM-000 Experiment 000."""

from model import TimedResponse, Transaction


COMMAND_MASK = 0xF0
COMMAND_VALUE = 0xA0
RESPONSE_PREFIX = 0x60
RESPONSE_DELAY_CYCLES = 6


def respond(request: int) -> TimedResponse | None:
    if request & COMMAND_MASK != COMMAND_VALUE:
        return None
    return TimedResponse(RESPONSE_PREFIX | (request & 0x0F), RESPONSE_DELAY_CYCLES)


def observe(request: int) -> Transaction:
    response = respond(request)
    if response is None:
        raise ValueError(f"unsupported synthetic request: 0x{request:02X}")
    return Transaction(request, response.value, response.delay_cycles)


TRAINING_REQUESTS = (0xA0, 0xA1, 0xA2, 0xA4, 0xA8, 0xAF)
HELD_OUT_REQUEST = 0xA7


def training_corpus() -> tuple[Transaction, ...]:
    return tuple(observe(request) for request in TRAINING_REQUESTS)

