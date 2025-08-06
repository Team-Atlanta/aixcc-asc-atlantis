from typing import Dict, List, Literal
import json
import re
import logging
import os
import litellm
import time
import tiktoken

from model import GPT4o
from abc import ABC, abstractmethod

"""
Prompt class is an abstract class that assembles system prompts, 
user prompts, and fewshot examples.
"""
logger = logging.getLogger("Completion")


class Completion(ABC):
    def __init__(
        self,
        system_prompt: str | None,
        user_prompt: list,
        model=GPT4o(),
        functions=None,
        function_call=None,
        response_format=None,
    ) -> None:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.model = model
        self.functions = functions
        self.function_call = function_call
        self.response_format = response_format

    def num_tokens_from_messages(self, messages, model="gpt-4o"):
        """Return the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl200k_base encoding.")
            encoding = tiktoken.get_encoding("cl200k_base")
        tokens_per_message = 3
        tokens_per_name = 1

        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens

    def cut_off_message(self, system_prompt, user_prompt, max_length=30000):
        accumulated_length = len(system_prompt) if system_prompt is not None else 0

        index = len(user_prompt) - 1
        while accumulated_length < max_length and index >= 0:
            message = user_prompt[index]
            if "question" in message:
                content_length = len(message["question"])
                if accumulated_length + content_length < max_length:
                    accumulated_length += content_length
                else:
                    message["question"] = message["question"][
                        : max_length - accumulated_length
                    ]
                    accumulated_length = max_length
            if "answer" in message:
                content_length = len(message["answer"])
                if accumulated_length + content_length < max_length:
                    accumulated_length += content_length
                else:
                    message["answer"] = message["answer"][
                        : max_length - accumulated_length
                    ]
                    accumulated_length = max_length

            index -= 1

    def create(self, llm_manager, temperature=1, top_p=1.0, num_samples: int = 1):
        start_time = time.time()

        while time.time() - start_time < 300:
            try:
                token = self.num_tokens_from_messages(self.to_messages())
                if token > 120000:
                    logger.warn("This input context is too long!")
                    self.cut_off_message(self.system_prompt, self.user_prompt)
            except Exception as e:
                logger.warn("Error in estimating the input length %s", e)

            try:
                if not llm_manager.has_cost_exceeded_limit():
                    return (["exceed"], 0.0)
                if llm_manager.is_rate_limited(self.model):
                    time.sleep(10)
                    continue

                response = litellm.completion(
                    model=self.model.name,
                    base_url=os.environ["AIXCC_LITELLM_HOSTNAME"],
                    api_key=os.environ["LITELLM_KEY"],
                    messages=self.to_messages(),
                    functions=self.functions,
                    # Define the function which needs to be called when the outmodelput has received
                    function_call=self.function_call,
                    temperature=temperature,
                    top_p=top_p,
                    n=num_samples,
                    response_format=self.response_format,
                    max_tokens=self.model.max_tokens,
                    custom_llm_provider=self.model.provider,
                )
                cost = self.completion_cost(completion_response=response)
                llm_manager.cost += cost

                response_message = response.choices[0].message

                # Check if function has called
                if response_message.get("content") is not None:
                    answer = [
                        choice["message"]["content"] for choice in response.choices
                    ]
                elif response_message.get("function_call") is not None:
                    # Define variables based on the response message
                    # function_to_run = response_message["function_call"].name
                    function_args = json.loads(
                        response_message["function_call"].arguments
                    )
                    answer = [str(function_args)]
                else:
                    answer = [""]
                return (answer, cost)

            except litellm.RateLimitError as e:
                llm_manager.rate_limit(self.model)
                logger.error("Rate limit Error %s", e)
            except litellm.Timeout as e:
                logger.error("Timeout occured %s", e)
                time.sleep(10)
            except Exception as e:
                logger.error("Unexpected error occured %s", e)
                time.sleep(10)

        return (["error"], 0.0)

    @abstractmethod
    def to_messages(self) -> List[Dict[str, str]]:
        pass

    def completion_cost(
        self,
        completion_response=None,
    ):
        prompt_tokens = 0
        completion_tokens = 0
        if completion_response is not None:
            prompt_tokens = completion_response.get("usage", {}).get("prompt_tokens", 0)
            completion_tokens = completion_response.get("usage", {}).get(
                "completion_tokens", 0
            )

        prompt_tokens_cost_usd_dollar = prompt_tokens * 0.000005
        completion_tokens_cost_usd_dollar = completion_tokens * 0.000015
        _final_cost = prompt_tokens_cost_usd_dollar + completion_tokens_cost_usd_dollar

        return _final_cost


class OpenAICompletion(Completion):
    def __init__(
        self,
        system_prompt: str | None,
        user_prompt: List,
        model=GPT4o(),
        functions=None,
        function_call=None,
    ) -> None:
        self.logger = logging.getLogger("OpenAICompletion")
        super().__init__(system_prompt, user_prompt, model, functions, function_call)

    def to_messages(self) -> List[Dict[str, str]]:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for example in self.user_prompt:
            messages.append({"role": "user", "content": example["question"]})
            if example["answer"] != "":
                messages.append({"role": "assistant", "content": example["answer"]})
        return messages

    def continue_chat(self, response, question):
        self.user_prompt[-1]["answer"] = response
        self.user_prompt.append({"question": question, "answer": ""})

    def parse_response(self, response: List, possible_answers) -> str:
        # Parsing response to json causes parse error
        # Therefore, check the result heuristicly
        try:
            json_str = response[0].strip("```json\n").strip("```")
            data = json.loads(json_str)
            answer = re.sub(r"^\d+\.\s*", "", data["answer"]).strip()

            if answer in possible_answers:
                return answer
            else:
                raise ValueError("Try heuristics because of invalid json keys.")
        except Exception:
            for possible_answer in possible_answers:
                if response[0][-20:].find(possible_answer) != -1:
                    return possible_answer

            if response[0] == "error":
                return "error"

            if response[0] == "exceed":
                return "exceed"

            self.logger.warn(f"Invalid response {json_str}")
            return "invalid"
