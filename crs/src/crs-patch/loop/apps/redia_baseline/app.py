import os

from loop.framework.circuit.models import Circuit
from loop.framework.wire.models import Wire
from loop.services.agents.redia import RediaAgent
from loop.services.environments.default import DefaultEnvironment
from loop.services.evaluators.acc import AccEvaluator
from loop.services.pickers.redia import RediaPicker

api_key = os.getenv("LITELLM_API_KEY", None)

assert api_key is not None, "Please set LITELLM_API_KEY environment variable"

base_url = os.getenv("LITELLM_BASE_URL", None)  # http://bombshell.gtisc.gatech.edu:4000

assert base_url is not None, "Please set LITELLM_BASE_URL environment variable"

app = Circuit(
    id="redia",
    wires=[
        lambda: Wire(
            id="gpt-4o-1",
            max_iteration=4,
            environment=DefaultEnvironment(),
            picker=RediaPicker(),
            agent=RediaAgent(
                lite_llm_context={
                    "api_key": api_key,
                    "base_url": base_url,
                    "max_tokens": 2048,
                    "model": "oai-gpt-4o",
                }
            ),
            evaluator=AccEvaluator(),
        ),
        lambda: Wire(
            id="gpt-4o-2",
            max_iteration=4,
            environment=DefaultEnvironment(),
            picker=RediaPicker(),
            agent=RediaAgent(
                lite_llm_context={
                    "api_key": api_key,
                    "base_url": base_url,
                    "max_tokens": 2048,
                    "model": "oai-gpt-4o",
                }
            ),
            evaluator=AccEvaluator(),
        ),
    ],
)

if __name__ == "__main__":
    run = app.runner_from_shell()
    run()
