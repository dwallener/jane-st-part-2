import json

from integrity_hypothesis import (
    CRC8_CATALOG,
    Xor8,
    frame_with_integrity,
    infer_integrity,
)


PAYLOADS = (
    (0x01, 0x02, 0x03),
    (0x10, 0x20),
    (0xFF, 0x00, 0x55, 0xAA),
    (0x31, 0x32, 0x33, 0x34),
)


def demonstrate(name, model):
    frames = tuple(frame_with_integrity(payload, model) for payload in PAYLOADS)
    result = infer_integrity(frames)
    return {
        "fixture": name,
        "candidate_count": len(result.candidates),
        "candidate": result.model.describe() if result.model is not None else None,
    }


ambiguous = infer_integrity(
    (
        (0x10, 0x20, 0x30),
        (0x11, 0x21, 0x30),
    )
)
probe = ambiguous.propose_probe()

print(
    json.dumps(
        {
            "resolved": [
                demonstrate("xor8", Xor8()),
                demonstrate("crc8_smbus", CRC8_CATALOG[0]),
                demonstrate("crc8_maxim_dow", CRC8_CATALOG[2]),
            ],
            "ambiguous": {
                "candidates": [item.describe() for item in ambiguous.candidates],
                "probe": {
                    "payload": list(probe.payload),
                    "predicted_trailers": list(probe.predicted_trailers),
                }
                if probe is not None
                else None,
            },
        },
        indent=2,
    )
)
