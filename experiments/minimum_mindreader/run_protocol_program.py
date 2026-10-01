import json

from model import learn
from protocol_program import compile_stateless, compile_toggle
from state_model import learn_toggle_machine
from stateful_peripheral import TOGGLE_COMMAND, training_sequences
from synthetic_peripheral import HELD_OUT_REQUEST, training_corpus


def show(response):
    if response is None:
        return "UNKNOWN"
    return {"value": f"0x{response.value:02X}", "delay_cycles": response.delay_cycles}


stateless = compile_stateless(learn(training_corpus()))
toggle_model = learn_toggle_machine(training_sequences()).model
assert toggle_model is not None
stateful = compile_toggle(toggle_model)

emulator = stateful.new_emulator()
before = emulator.emulate(HELD_OUT_REQUEST)
toggle = emulator.emulate(TOGGLE_COMMAND)
after = emulator.emulate(HELD_OUT_REQUEST)

print(
    json.dumps(
        {
            "record_bytes": 10,
            "stateless": {
                "transitions": len(stateless.transitions),
                "encoded_bytes": stateless.encoded_bytes,
                "held_out": show(stateless.new_emulator().emulate(HELD_OUT_REQUEST)),
            },
            "two_state": {
                "transitions": len(stateful.transitions),
                "encoded_bytes": stateful.encoded_bytes,
                "held_out_before_toggle": show(before),
                "toggle": show(toggle),
                "held_out_after_toggle": show(after),
            },
        },
        indent=2,
    )
)
