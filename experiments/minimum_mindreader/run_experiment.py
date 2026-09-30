"""Run and print the minimum mindreader held-out experiment."""

import json

from model import ReplayBaseline, learn
from edge_trace import strip_markers
from synthetic_link import encode_transaction, infer_transaction
from synthetic_peripheral import HELD_OUT_REQUEST, training_corpus


def format_response(response: object) -> object:
    if response is None:
        return None
    return {
        "value": f"0x{response.value:02X}",
        "delay_cycles": response.delay_cycles,
    }


def main() -> None:
    annotated_traces = tuple(encode_transaction(item) for item in training_corpus())
    traces = tuple(strip_markers(trace) for trace in annotated_traces)
    corpus = tuple(infer_transaction(trace) for trace in traces)
    replay = ReplayBaseline(corpus)
    model = learn(corpus)

    result = {
        "training_requests": [f"0x{item.request:02X}" for item in corpus],
        "trace_event_counts": [len(trace.events) for trace in traces],
        "supplied_markers": False,
        "held_out_request": f"0x{HELD_OUT_REQUEST:02X}",
        "replay_result": format_response(replay.emulate(HELD_OUT_REQUEST)),
        "learned_model": model.describe(),
        "learned_result": format_response(model.emulate(HELD_OUT_REQUEST)),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
