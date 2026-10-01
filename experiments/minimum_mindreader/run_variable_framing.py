import json

from test_variable_framing import (
    AMBIGUOUS_TRAINING,
    DELIMITER_TRAINING,
    LENGTH_TRAINING,
)
from variable_framing import learn_variable_framing


def describe(name, frames, held_out_stream):
    result = learn_variable_framing(frames)
    parsed = result.model.parse(held_out_stream) if result.model is not None else None
    return {
        "name": name,
        "evidence_count": result.evidence_count,
        "candidates": [candidate.describe() for candidate in result.candidates],
        "held_out_frames": parsed,
    }


print(
    json.dumps(
        [
            describe(
                "length",
                LENGTH_TRAINING,
                (0x03, 0xAA, 0xBB, 0xCC, 0x01, 0xDD),
            ),
            describe(
                "delimiter",
                DELIMITER_TRAINING,
                (0x44, 0x45, 0x7E, 0x55, 0x7E),
            ),
            describe("ambiguous", AMBIGUOUS_TRAINING, (0x02, 0x44, 0x7E)),
        ],
        indent=2,
    )
)
