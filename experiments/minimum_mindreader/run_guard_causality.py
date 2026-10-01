from guard_causality import analyze_program_guards
from hierarchical_model import build_hierarchical_spi_model
from spi_behavior import make_spi_behavior_corpus


for mode in range(4):
    for msb_first in (True, False):
        model = build_hierarchical_spi_model(
            make_spi_behavior_corpus(mode, msb_first)
        )
        result = analyze_program_guards(model.program)[0]
        print(
            f"mode={mode} fixture_order={'msb' if msb_first else 'lsb'} "
            f"decision_time={result.decision_time} risk={result.risk.value} "
            f"dependent={result.speculative_dependent_bits}"
        )
