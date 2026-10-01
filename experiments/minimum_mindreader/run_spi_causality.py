from hierarchical_model import build_hierarchical_spi_model
from spi_behavior import make_spi_behavior_corpus
from spi_causality import analyze_spi_causality


for mode in range(4):
    for msb_first in (True, False):
        artifact = build_hierarchical_spi_model(
            make_spi_behavior_corpus(mode, msb_first)
        )
        analysis = analyze_spi_causality(
            artifact.program,
            sampling_edge=artifact.physical.sampling_edge,
        )
        print(
            f"mode={mode} fixture_order={'msb' if msb_first else 'lsb'} "
            f"class={analysis.classification.value} "
            f"requirements={','.join(item.value for item in analysis.timing_requirements)}"
        )
