"""Pin-level fixture codec for CLAIM-000 Experiment 001."""

from __future__ import annotations

from edge_trace import Marker, Trace, TraceBuilder
from model import Transaction


CLOCK = 1 << 0
REQUEST_DATA = 1 << 1
SELECT = 1 << 2
RESPONSE_DATA = 1 << 0
RESPONSE_VALID = 1 << 1
BYTE_BITS = 8


def _with_bit(value: int, mask: int, bit: int) -> int:
    return (value | mask) if bit else (value & ~mask)


def encode_transaction(transaction: Transaction) -> Trace:
    builder = TraceBuilder()
    builder.wait(1)
    builder.emit(input_value=SELECT, marker=Marker.REQUEST_START)

    for bit_index in reversed(range(BYTE_BITS)):
        bit = (transaction.request >> bit_index) & 1
        next_input = _with_bit(builder.input_value, REQUEST_DATA, bit)
        builder.wait(1)
        if next_input != builder.input_value:
            builder.emit(input_value=next_input)
        builder.wait(1)
        builder.emit(input_value=builder.input_value | CLOCK)
        builder.wait(1)
        builder.emit(input_value=builder.input_value & ~CLOCK)

    builder.emit(marker=Marker.REQUEST_END)
    builder.wait(transaction.delay_cycles)
    builder.emit(
        output_value=builder.output_value | RESPONSE_VALID,
        marker=Marker.RESPONSE_START,
    )

    for bit_index in reversed(range(BYTE_BITS)):
        bit = (transaction.response >> bit_index) & 1
        next_output = _with_bit(builder.output_value, RESPONSE_DATA, bit)
        builder.wait(1)
        if next_output != builder.output_value:
            builder.emit(output_value=next_output)
        builder.wait(1)
        builder.emit(input_value=builder.input_value | CLOCK)
        builder.wait(1)
        builder.emit(input_value=builder.input_value & ~CLOCK)

    builder.emit(
        input_value=0,
        output_value=0,
        marker=Marker.RESPONSE_END,
    )
    return builder.build()


def _bits_to_byte(bits: list[int], phase: str) -> int:
    if len(bits) != BYTE_BITS:
        raise ValueError(f"{phase} contains {len(bits)} sampled bits; expected 8")
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def decode_transaction(trace: Trace) -> Transaction:
    request_bits: list[int] = []
    response_bits: list[int] = []
    marker_cycles: dict[Marker, int] = {}
    marker_order: list[Marker] = []
    phase: Marker | None = None
    cycle = 0
    previous_input = 0

    for event in trace.events:
        cycle += event.delta_cycles
        if event.marker is not None:
            if event.marker in marker_cycles:
                raise ValueError(f"duplicate marker: {event.marker.value}")
            marker_cycles[event.marker] = cycle
            marker_order.append(event.marker)
            if event.marker is Marker.REQUEST_START:
                phase = Marker.REQUEST_START
            elif event.marker is Marker.REQUEST_END:
                phase = None
            elif event.marker is Marker.RESPONSE_START:
                phase = Marker.RESPONSE_START
            elif event.marker is Marker.RESPONSE_END:
                phase = None

        rising_edge = not (previous_input & CLOCK) and bool(event.input_value & CLOCK)
        if rising_edge:
            if not event.input_value & SELECT:
                raise ValueError("clock edge occurred while select was inactive")
            if phase is Marker.REQUEST_START:
                request_bits.append(bool(event.input_value & REQUEST_DATA))
            elif phase is Marker.RESPONSE_START:
                response_bits.append(bool(event.output_value & RESPONSE_DATA))
        previous_input = event.input_value

    expected_order = [
        Marker.REQUEST_START,
        Marker.REQUEST_END,
        Marker.RESPONSE_START,
        Marker.RESPONSE_END,
    ]
    if marker_order != expected_order:
        observed = [marker.value for marker in marker_order]
        raise ValueError(f"unexpected marker order: {observed}")

    request = _bits_to_byte([int(bit) for bit in request_bits], "request")
    response = _bits_to_byte([int(bit) for bit in response_bits], "response")
    delay_cycles = (
        marker_cycles[Marker.RESPONSE_START] - marker_cycles[Marker.REQUEST_END]
    )
    return Transaction(request, response, delay_cycles)


def infer_transaction(trace: Trace) -> Transaction:
    """Recover one synthetic-link transaction without boundary annotations."""

    if any(event.marker is not None for event in trace.events):
        raise ValueError("inference input must not contain supplied markers")

    request_bits: list[int] = []
    response_bits: list[int] = []
    cycle = 0
    previous_input = 0
    previous_output = 0
    request_end_cycle: int | None = None
    response_start_cycle: int | None = None
    saw_select = False

    for event in trace.events:
        cycle += event.delta_cycles
        select_rising = not (previous_input & SELECT) and bool(event.input_value & SELECT)
        select_falling = bool(previous_input & SELECT) and not (event.input_value & SELECT)
        valid_rising = not (previous_output & RESPONSE_VALID) and bool(
            event.output_value & RESPONSE_VALID
        )
        valid_falling = bool(previous_output & RESPONSE_VALID) and not (
            event.output_value & RESPONSE_VALID
        )
        clock_rising = not (previous_input & CLOCK) and bool(event.input_value & CLOCK)
        clock_falling = bool(previous_input & CLOCK) and not (event.input_value & CLOCK)

        if select_rising:
            if saw_select:
                raise ValueError("multiple select assertions in one trace")
            saw_select = True
        if valid_rising:
            if not saw_select or response_start_cycle is not None:
                raise ValueError("invalid response-valid assertion")
            response_start_cycle = cycle
        if valid_falling and not select_falling:
            raise ValueError("response-valid ended before the transaction")

        if clock_rising:
            if not event.input_value & SELECT:
                raise ValueError("clock edge occurred while select was inactive")
            if event.output_value & RESPONSE_VALID:
                response_bits.append(int(bool(event.output_value & RESPONSE_DATA)))
            else:
                request_bits.append(int(bool(event.input_value & REQUEST_DATA)))
        if clock_falling and len(request_bits) == BYTE_BITS and request_end_cycle is None:
            request_end_cycle = cycle

        if select_falling:
            if event.output_value & RESPONSE_VALID:
                raise ValueError("select ended while response-valid remained asserted")

        previous_input = event.input_value
        previous_output = event.output_value

    if not saw_select:
        raise ValueError("no transaction select assertion observed")
    if previous_input != 0 or previous_output != 0:
        raise ValueError("trace ended before pins returned to idle")
    if request_end_cycle is None:
        raise ValueError("request completion was not observed")
    if response_start_cycle is None:
        raise ValueError("response start is unobservable without response-valid")
    if response_start_cycle < request_end_cycle:
        raise ValueError("response began before the request completed")

    request = _bits_to_byte(request_bits, "request")
    response = _bits_to_byte(response_bits, "response")
    return Transaction(
        request=request,
        response=response,
        delay_cycles=response_start_cycle - request_end_cycle,
    )
