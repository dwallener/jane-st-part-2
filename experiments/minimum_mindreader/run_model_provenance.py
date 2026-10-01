import json

from hierarchical_model import build_hierarchical_spi_model
from model_provenance import build_spi_provenance
from spi_behavior import make_spi_behavior_corpus, reversible_response


def describe(response_function=None):
    kwargs = {"response_function": response_function} if response_function else {}
    corpus = make_spi_behavior_corpus(3, False, **kwargs)
    bundle = build_spi_provenance(corpus)
    return {
        "sidecar_bytes": bundle.encoded_bytes,
        "claims": [
            {
                "kind": claim.kind.name.lower(),
                "status": claim.status.name.lower(),
                "support_count": len(bundle.supported_evidence(claim)),
            }
            for claim in bundle.claims
        ],
        "probe": bundle.probe.kind.name.lower(),
    }


resolved_corpus = make_spi_behavior_corpus(3, False)
core = build_hierarchical_spi_model(resolved_corpus)
resolved = build_spi_provenance(resolved_corpus)
print(
    json.dumps(
        {
            "core_bytes": core.encoded_bytes,
            "resolved": describe(),
            "core_plus_resolved_sidecar_bytes": core.encoded_bytes
            + resolved.encoded_bytes,
            "reversible": describe(reversible_response),
        },
        indent=2,
    )
)
