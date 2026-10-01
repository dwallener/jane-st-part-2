import unittest

from hierarchical_model import build_hierarchical_spi_model
from model_provenance import (
    ClaimKind,
    ClaimStatus,
    ModelOrigin,
    ProbeKind,
    ProvenanceBundle,
    build_spi_provenance,
    waveform_fingerprint,
)
from spi_behavior import make_spi_behavior_corpus, reversible_response


class ModelProvenanceTest(unittest.TestCase):
    def test_resolved_spi_bundle_tracks_support_and_equivalence(self) -> None:
        corpus = make_spi_behavior_corpus(3, False)
        bundle = build_spi_provenance(corpus)

        self.assertEqual(bundle.origin, ModelOrigin.LEARNED)
        self.assertEqual(len(bundle.evidence), 8)
        self.assertEqual(len({record.fingerprint for record in bundle.evidence}), 8)
        self.assertEqual(
            bundle.claim(ClaimKind.PHYSICAL_TOPOLOGY).status,
            ClaimStatus.SUPPORTED,
        )
        self.assertEqual(
            bundle.claim(ClaimKind.DATA_DIRECTION).status,
            ClaimStatus.SUPPORTED,
        )
        self.assertEqual(
            bundle.claim(ClaimKind.BEHAVIOR_TRANSITION).status,
            ClaimStatus.SUPPORTED,
        )
        self.assertEqual(
            bundle.claim(ClaimKind.BIT_ORDER).status,
            ClaimStatus.EQUIVALENT,
        )
        self.assertEqual(bundle.probe.kind, ProbeKind.NONE)
        self.assertEqual(
            len(bundle.supported_evidence(bundle.claim(ClaimKind.BEHAVIOR_TRANSITION))),
            8,
        )

    def test_resolved_sidecar_is_fifty_six_bytes(self) -> None:
        corpus = make_spi_behavior_corpus(0, True)
        bundle = build_spi_provenance(corpus)
        core = build_hierarchical_spi_model(corpus)

        self.assertEqual(bundle.encoded_bytes, 56)
        self.assertEqual(core.encoded_bytes, 22)
        self.assertEqual(bundle.encoded_bytes + core.encoded_bytes, 78)
        self.assertEqual(ProvenanceBundle.decode(bundle.encode()), bundle)

    def test_reversible_behavior_names_missing_electrical_evidence(self) -> None:
        corpus = make_spi_behavior_corpus(
            0, True, response_function=reversible_response
        )
        bundle = build_spi_provenance(corpus)

        self.assertEqual(
            bundle.claim(ClaimKind.DATA_DIRECTION).status,
            ClaimStatus.UNRESOLVED,
        )
        self.assertEqual(
            bundle.claim(ClaimKind.BEHAVIOR_TRANSITION).status,
            ClaimStatus.UNRESOLVED,
        )
        self.assertEqual(bundle.probe.kind, ProbeKind.OBSERVE_DRIVE_OWNERSHIP)
        self.assertEqual(
            bundle.claim(ClaimKind.BIT_ORDER).status,
            ClaimStatus.EQUIVALENT,
        )

    def test_fingerprint_changes_with_waveform_evidence(self) -> None:
        corpus = make_spi_behavior_corpus(0, True)

        self.assertNotEqual(
            waveform_fingerprint(corpus[0].waveform),
            waveform_fingerprint(corpus[1].waveform),
        )

    def test_corrupt_and_truncated_sidecars_are_rejected(self) -> None:
        encoded = bytearray(build_spi_provenance(make_spi_behavior_corpus(0, True)).encode())
        encoded[0] ^= 0x01
        with self.assertRaisesRegex(ValueError, "magic"):
            ProvenanceBundle.decode(bytes(encoded))

        valid = build_spi_provenance(make_spi_behavior_corpus(0, True)).encode()
        with self.assertRaisesRegex(ValueError, "length"):
            ProvenanceBundle.decode(valid[:-1])


if __name__ == "__main__":
    unittest.main()
