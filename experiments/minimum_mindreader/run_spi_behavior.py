import json

from spi_behavior import (
    HELD_OUT_REQUEST,
    infer_spi_behavior,
    lossy_response,
    make_spi_behavior_corpus,
)
from spi_hypothesis import SpiBitOrder


corpus = make_spi_behavior_corpus(3, False)
result = infer_spi_behavior(corpus)
ground_truth_order = next(
    candidate
    for candidate in result.candidates
    if candidate.hypothesis.bit_order is SpiBitOrder.LSB_FIRST
)
response = ground_truth_order.compile().new_emulator().emulate(HELD_OUT_REQUEST)

print(
    json.dumps(
        {
            "waveforms": result.waveform_count,
            "physical_hypotheses_per_waveform": result.physical_hypotheses_per_waveform,
            "survivors": len(result.candidates),
            "resolved_request_pin": list(result.request_pins),
            "resolved_response_pin": list(result.response_pins),
            "remaining_bit_orders": [order.value for order in result.bit_orders],
            "compiled_bytes_per_candidate": [
                candidate.compile().encoded_bytes for candidate in result.candidates
            ],
            "held_out": {
                "request": f"0x{HELD_OUT_REQUEST:02X}",
                "expected": f"0x{lossy_response(HELD_OUT_REQUEST):02X}",
                "actual": f"0x{response.value:02X}" if response is not None else None,
                "delay_cycles": response.delay_cycles if response is not None else None,
            },
        },
        indent=2,
    )
)
