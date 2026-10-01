import json

from framing_hypothesis import FramingHypothesis, PinRoles
from model import Transaction
from synthetic_peripheral import training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant
from width_hypothesis import infer_width


def describe(frame_width: int, traces):
    hypothesis = FramingHypothesis(SamplingEdge.RISING, BitOrder.MSB_FIRST)
    result = infer_width(tuple(traces), hypothesis, PinRoles())
    return {
        "fixture_frame_width": frame_width,
        "observed_request_bits": result.phase_shape.request_bits,
        "observed_response_bits": result.phase_shape.response_bits,
        "compatible_symbol_widths": list(result.symbol_widths),
        "possible_request_segmentations": [
            {
                "symbol_width": width,
                "symbol_count": result.symbols_per_request(width),
            }
            for width in result.symbol_widths
        ],
    }


eight_bit_traces = (
    encode_variant(item, SamplingEdge.RISING, BitOrder.MSB_FIRST)
    for item in training_corpus()
)
six_bit_traces = (
    encode_variant(
        Transaction(request, request ^ 0x15, 4),
        SamplingEdge.RISING,
        BitOrder.MSB_FIRST,
        frame_width=6,
    )
    for request in (0x00, 0x03, 0x0C, 0x2A)
)

print(json.dumps([describe(8, eight_bit_traces), describe(6, six_bit_traces)], indent=2))
