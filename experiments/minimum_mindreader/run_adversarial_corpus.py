import json
from dataclasses import asdict
from adversarial_corpus import run_adversarial_corpus
print(json.dumps([asdict(result) for result in run_adversarial_corpus()], indent=2))
