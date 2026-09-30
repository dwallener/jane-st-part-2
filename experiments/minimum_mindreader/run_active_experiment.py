"""Run active disambiguation against the synthetic peripheral."""

import json

from active_model import expand_hypotheses
from synthetic_peripheral import HELD_OUT_REQUEST, observe, respond


def main() -> None:
    hypotheses = expand_hypotheses((observe(0xA0), observe(0xAF)))
    initial_count = len(hypotheses.candidates)
    probes = []

    while not hypotheses.is_resolved:
        suggestion = hypotheses.suggest_probe()
        if suggestion is None:
            raise RuntimeError("remaining hypotheses cannot be separated")
        response = respond(suggestion.request)
        if response is None:
            raise RuntimeError("proposed probe is unsupported by the peripheral")
        before = len(hypotheses.candidates)
        hypotheses = hypotheses.observe(suggestion.request, response)
        probes.append(
            {
                "request": f"0x{suggestion.request:02X}",
                "response": f"0x{response.value:02X}",
                "distinct_predicted_outcomes": suggestion.distinct_outcomes,
                "worst_case_before_observation": suggestion.worst_case_remaining,
                "candidates_before": before,
                "candidates_after": len(hypotheses.candidates),
            }
        )

    model = hypotheses.resolved_model
    assert model is not None
    held_out = model.emulate(HELD_OUT_REQUEST)
    print(
        json.dumps(
            {
                "initial_candidate_count": initial_count,
                "probes": probes,
                "resolved": hypotheses.is_resolved,
                "held_out_request": f"0x{HELD_OUT_REQUEST:02X}",
                "held_out_response": (
                    None
                    if held_out is None
                    else {
                        "value": f"0x{held_out.value:02X}",
                        "delay_cycles": held_out.delay_cycles,
                    }
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

