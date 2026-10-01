import json

from framing_hypothesis import infer_framing
from synthetic_peripheral import training_corpus
from variant_link import BitOrder, SamplingEdge, encode_variant


def run(edge: SamplingEdge, order: BitOrder) -> dict[str, object]:
    traces = tuple(encode_variant(item, edge, order) for item in training_corpus())
    result = infer_framing(traces)
    return {
        "fixture": {"sampling_edge": edge.value, "bit_order": order.value},
        "survivors": [
            {
                "sampling_edge": item.hypothesis.sampling_edge.value,
                "bit_order": item.hypothesis.bit_order.value,
                "model_complete": item.model.is_complete,
            }
            for item in result.candidates
        ],
        "rejected": [
            {
                "sampling_edge": hypothesis.sampling_edge.value,
                "bit_order": hypothesis.bit_order.value,
                "reason": reason,
            }
            for hypothesis, reason in result.rejected
        ],
    }


print(
    json.dumps(
        [
            run(SamplingEdge.RISING, BitOrder.MSB_FIRST),
            run(SamplingEdge.FALLING, BitOrder.LSB_FIRST),
        ],
        indent=2,
    )
)
