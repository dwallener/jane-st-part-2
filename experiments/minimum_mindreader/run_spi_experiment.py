import json

from known_protocol_corpus import benchmark_cases
from spi_hypothesis import infer_spi


results = []
for case in benchmark_cases():
    if case.truth.family != "SPI":
        continue
    inference = infer_spi(case.inference_input())
    results.append(
        {
            "case": case.name,
            "hypotheses_tested": inference.hypothesis_count,
            "survivors": len(inference.candidates),
            "select_pin": list(inference.select_pins),
            "clock_pin": list(inference.clock_pins),
            "select_active_level": list(inference.select_active_levels),
            "clock_idle_level": list(inference.clock_idle_levels),
            "sampling_edge": [edge.value for edge in inference.sampling_edges],
            "remaining_symmetries": {
                "data_direction_labels": 2,
                "bit_orders": [order.value for order in inference.bit_orders],
            },
        }
    )

print(json.dumps(results, indent=2))
