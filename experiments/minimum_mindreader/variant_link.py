"""Synthetic serial link with configurable sampling edge and bit order."""

from __future__ import annotations

from enum import Enum

from edge_trace import Trace, TraceBuilder, TraceEvent
from model import Transaction
from synthetic_link import (
    BYTE_BITS,
    CLOCK,
    REQUEST_DATA,
    RESPONSE_DATA,
    RESPONSE_VALID,
    SELECT,
)


class SamplingEdge(Enum):
    RISING = "rising"
    FALLING = "falling"


class BitOrder(Enum):
    MSB_FIRST = "msb_first"
    LSB_FIRST = "lsb_first"


def _bits(value: int, bit_order: BitOrder) -> tuple[int, ...]:
    indices = (
        reversed(range(BYTE_BITS))
        if bit_order is BitOrder.MSB_FIRST
        else range(BYTE_BITS)
    )
    return tuple((value >> bit) & 1 for bit in indices)


def _with_bit(value: int, mask: int, bit: int) -> int:
    return (value | mask) if bit else (value & ~mask)


def _emit_request_byte(
    builder: TraceBuilder, bits: tuple[int, ...], sampling_edge: SamplingEdge
) -> None:
    for index, bit in enumerate(bits):
        if sampling_edge is SamplingEdge.FALLING:
            next_input = _with_bit(builder.input_value, REQUEST_DATA, bit)
            builder.wait(1)
            builder.emit(input_value=next_input | CLOCK)
            builder.wait(1)
            builder.emit(input_value=builder.input_value & ~CLOCK)
        else:
            builder.wait(1)
            builder.emit(input_value=builder.input_value | CLOCK)
            next_bit = bits[index + 1] if index + 1 < len(bits) else bit
            next_input = _with_bit(builder.input_value & ~CLOCK, REQUEST_DATA, next_bit)
            builder.wait(1)
            builder.emit(input_value=next_input)


def _emit_response_byte(
    builder: TraceBuilder, bits: tuple[int, ...], sampling_edge: SamplingEdge
) -> None:
    for index, bit in enumerate(bits):
        if sampling_edge is SamplingEdge.FALLING:
            next_output = _with_bit(builder.output_value, RESPONSE_DATA, bit)
            builder.wait(1)
            builder.emit(
                input_value=builder.input_value | CLOCK,
                output_value=next_output,
            )
            builder.wait(1)
            builder.emit(input_value=builder.input_value & ~CLOCK)
        else:
            builder.wait(1)
            builder.emit(input_value=builder.input_value | CLOCK)
            next_bit = bits[index + 1] if index + 1 < len(bits) else bit
            next_output = _with_bit(builder.output_value, RESPONSE_DATA, next_bit)
            builder.wait(1)
            builder.emit(
                input_value=builder.input_value & ~CLOCK,
                output_value=next_output,
            )


def encode_variant(
    transaction: Transaction,
    sampling_edge: SamplingEdge,
    bit_order: BitOrder,
) -> Trace:
    """Encode an unannotated trace with data changing on non-sampling edges."""

    request_bits = _bits(transaction.request, bit_order)
    response_bits = _bits(transaction.response, bit_order)
    builder = TraceBuilder()

    builder.wait(1)
    builder.emit(
        input_value=_with_bit(SELECT, REQUEST_DATA, request_bits[0]),
    )
    _emit_request_byte(builder, request_bits, sampling_edge)

    builder.wait(transaction.delay_cycles)
    builder.emit(
        output_value=_with_bit(RESPONSE_VALID, RESPONSE_DATA, response_bits[0]),
    )
    _emit_response_byte(builder, response_bits, sampling_edge)

    builder.emit(input_value=0, output_value=0)
    return builder.build()


def _remap_value(value: int, mapping: dict[int, int]) -> int:
    remapped = value
    for source in mapping:
        remapped &= ~source
    for source, destination in mapping.items():
        if value & source:
            remapped |= destination
    return remapped


def remap_pins(
    trace: Trace,
    *,
    input_mapping: dict[int, int],
    output_mapping: dict[int, int],
) -> Trace:
    """Move logical link signals to alternate one-hot physical pin masks."""

    if len(set(input_mapping.values())) != len(input_mapping):
        raise ValueError("input pin destinations must be unique")
    if len(set(output_mapping.values())) != len(output_mapping):
        raise ValueError("output pin destinations must be unique")
    if any(mask <= 0 or mask & (mask - 1) for mask in (*input_mapping, *output_mapping)):
        raise ValueError("pin sources must be one-hot masks")
    if any(
        mask <= 0 or mask & (mask - 1)
        for mask in (*input_mapping.values(), *output_mapping.values())
    ):
        raise ValueError("pin destinations must be one-hot masks")

    events: list[TraceEvent] = []
    previous_input = 0
    previous_output = 0
    for event in trace.events:
        input_value = _remap_value(event.input_value, input_mapping)
        output_value = _remap_value(event.output_value, output_mapping)
        events.append(
            TraceEvent(
                delta_cycles=event.delta_cycles,
                input_value=input_value,
                input_changed=previous_input ^ input_value,
                output_value=output_value,
                output_changed=previous_output ^ output_value,
                marker=event.marker,
            )
        )
        previous_input = input_value
        previous_output = output_value
    return Trace(tuple(events))
