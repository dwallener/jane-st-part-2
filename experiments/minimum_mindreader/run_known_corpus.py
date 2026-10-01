import json

from known_protocol_corpus import benchmark_cases


cases = benchmark_cases()
families = sorted({case.truth.family for case in cases})
print(
    json.dumps(
        {
            "case_count": len(cases),
            "families": {
                family: [case.name for case in cases if case.truth.family == family]
                for family in families
            },
            "inference_inputs_contain": "anonymous indexed-pin waveforms only",
            "status": "reference fixtures validated; learner scoring not yet wired",
        },
        indent=2,
    )
)
