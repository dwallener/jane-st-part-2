import json

from hierarchical_model import build_hierarchical_spi_model
from spi_behavior import make_spi_behavior_corpus


artifact = build_hierarchical_spi_model(make_spi_behavior_corpus(3, False))
round_trip = type(artifact).decode(artifact.encode())
print(
    json.dumps(
        {
            **artifact.describe(),
            "hex": artifact.encode().hex(),
            "round_trip_equal": round_trip == artifact,
        },
        indent=2,
    )
)
