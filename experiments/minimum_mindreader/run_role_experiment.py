import json

from framing_hypothesis import PinRoles
from role_hypothesis import infer_pin_roles
from synthetic_link import CLOCK, REQUEST_DATA, RESPONSE_DATA, RESPONSE_VALID, SELECT
from synthetic_peripheral import training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant, remap_pins


expected = PinRoles(
    clock=0x04,
    request_data=0x01,
    select=0x02,
    response_data=0x02,
    response_valid=0x01,
)
traces = tuple(
    remap_pins(
        encode_variant(item, SamplingEdge.FALLING, BitOrder.LSB_FIRST),
        input_mapping={
            CLOCK: expected.clock,
            REQUEST_DATA: expected.request_data,
            SELECT: expected.select,
        },
        output_mapping={
            RESPONSE_DATA: expected.response_data,
            RESPONSE_VALID: expected.response_valid,
        },
    )
    for item in training_corpus()
)
result = infer_pin_roles(traces)

print(
    json.dumps(
        {
            "hypotheses_tested": result.hypothesis_count,
            "survivors": [
                {
                    "clock": f"0x{candidate.roles.clock:02X}",
                    "request_data": f"0x{candidate.roles.request_data:02X}",
                    "select": f"0x{candidate.roles.select:02X}",
                    "response_data": f"0x{candidate.roles.response_data:02X}",
                    "response_valid": f"0x{candidate.roles.response_valid:02X}",
                    "sampling_edge": candidate.framing.hypothesis.sampling_edge.value,
                    "bit_order": candidate.framing.hypothesis.bit_order.value,
                }
                for candidate in result.candidates
            ],
        },
        indent=2,
    )
)
