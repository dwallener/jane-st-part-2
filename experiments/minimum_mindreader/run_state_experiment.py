"""Run the two-state held-out experiment and print its result."""

import json

from state_model import learn_toggle_machine
from stateful_peripheral import (
    HELD_OUT_REQUEST,
    TOGGLE_COMMAND,
    training_sequences,
)


def describe(response: object) -> object:
    if response is None:
        return None
    return {
        "value": f"0x{response.value:02X}",
        "delay_cycles": response.delay_cycles,
    }


def main() -> None:
    result = learn_toggle_machine(training_sequences())
    model = result.model
    if model is None:
        raise RuntimeError(
            f"state model is ambiguous: {[hex(item) for item in result.candidate_requests]}"
        )

    emulator = model.new_emulator()
    state_zero = emulator.state
    first = emulator.emulate(HELD_OUT_REQUEST)
    control = emulator.emulate(TOGGLE_COMMAND)
    state_one = emulator.state
    second = emulator.emulate(HELD_OUT_REQUEST)

    print(
        json.dumps(
            {
                "inferred_control_request": f"0x{model.control_request:02X}",
                "held_out_request": f"0x{HELD_OUT_REQUEST:02X}",
                "state_before_toggle": state_zero,
                "response_before_toggle": describe(first),
                "toggle_response": describe(control),
                "state_after_toggle": state_one,
                "response_after_toggle": describe(second),
                "candidate_count": len(result.candidates),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

