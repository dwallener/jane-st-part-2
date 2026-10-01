import json

from known_protocol_corpus import benchmark_cases
from waveform_adapter import score_current_frontend


scores = tuple(score_current_frontend(case) for case in benchmark_cases())
print(
    json.dumps(
        {
            "case_count": len(scores),
            "deepest_layer_counts": {
                layer: sum(score.deepest_passed_layer == layer for score in scores)
                for layer in sorted({score.deepest_passed_layer for score in scores})
            },
            "families": {
                family: {
                    "cases": sum(score.family == family for score in scores),
                    "deepest_layers": sorted(
                        {
                            score.deepest_passed_layer
                            for score in scores
                            if score.family == family
                        }
                    ),
                    "frontend_gap": next(
                        score.layers[-1].reason
                        for score in scores
                        if score.family == family
                    ),
                }
                for family in sorted({score.family for score in scores})
            },
        },
        indent=2,
    )
)
