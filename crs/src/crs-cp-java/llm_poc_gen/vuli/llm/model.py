from vuli.common.decorators import consume_exc_method
import litellm
import openai
import os


class Model:
    api_key = ""
    model = ""
    provider = ""
    temperature = 1
    top_p = 1
    n = 1
    max_tokens = 4096

    def __init__(
        self,
        api_key,
        model="oai-gpt-4o",
        provider="openai",
        temperature=1,
        top_p=1,
        n=1,
        max_tokens=4096,
    ):
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.top_p = top_p
        self.n = n
        self.max_tokens = max_tokens

    @consume_exc_method(default=(400, [], 0.0))
    def query(self, prompt: any) -> tuple[int, list[str], float]:
        try:
            response = litellm.completion(
                model=self.model,
                api_key=self.api_key,
                base_url=os.getenv(
                    "AIXCC_LITELLM_HOSTNAME", "http://bombshell.gtisc.gatech.edu:4000"
                ),
                temperature=self.temperature,
                top_p=self.top_p,
                n=self.n,
                custom_llm_provider=self.provider,
                max_tokens=self.max_tokens,
                messages=prompt,
                timeout=60,
            )
            cost = self.completion_cost(response)
            return (
                200,
                [choice["message"]["content"] for choice in response.choices],
                cost,
            )

        except openai.APIStatusError as e:
            return (e.status_code, [], 0)

    @consume_exc_method(default=0.0)
    def completion_cost(self, completion_response) -> float:
        usage = completion_response.get("usage", {})
        prompt_tokens: int = usage.get("prompt_tokens", 0)
        completion_tokens: int = usage.get("completion_tokens", 0)
        prompt_cost_in_usd: float = prompt_tokens * 0.000005
        completion_cost_in_usd: float = completion_tokens * 0.000015
        return prompt_cost_in_usd + completion_cost_in_usd
