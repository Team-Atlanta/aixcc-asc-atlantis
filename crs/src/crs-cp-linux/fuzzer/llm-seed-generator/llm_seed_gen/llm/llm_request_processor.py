import inspect
import os
import json
import litellm
import tiktoken

import time


class LLMRequestProcessor:
    total_cost = 0.0
    total_delay = 0

    def __init__(self, model) -> None:
        self.model = model

        self.message = []
        self.tools = []
        self.funcs = {}

        # get litellm url and key
        self.litellm_url = os.getenv("LITELLM_URL")
        self.litellm_key = os.getenv("LITELLM_KEY")

        # set environment variables
        os.environ["OPENAI_API_KEY"] = self.litellm_key
        os.environ["ANTHROPIC_API_KEY"] = self.litellm_key

        self.cost = 0.0
        self.delayed_time = 0

        # litellm.set_verbose = True

        self.context_window = self.model.context_window
        self.max_tokens = self.model.max_tokens
        self.token_threshold = self.context_window - self.max_tokens * 5

    def __del__(self):
        print(f'[INFO] LLMRequestProcessor instance used {self.cost}')
        print(f'[INFO] LLMRequestProcessor was delayed {self.delayed_time} seconds')

    def new_session(self) -> None:
        self.message = []

    def add_tool(self, func, tool):
        self.tools.append(tool)
        func_name = tool['function']['name']
        self.funcs[func_name] = func

    def clear_tools(self):
        self.tools = []
        self.funcs = {}

    def _add_message(self, role, message):
        new_message = {
            'role': role,
            'content': message
        }
        self.message.append(new_message)

    def _add_returned_message(self, message):
        self.message.append(dict(message))

    def _add_tool_message(self, tool_call_id, function_name, function_response):
        new_message = {
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": function_name,
            "content": function_response,
        }
        prev_tokens = self._count_tokens(self.message)
        new_tokens = self._count_tokens([new_message])

        if prev_tokens + new_tokens < self.token_threshold:
            self.message.append(new_message)
        else:
            error_message = {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": "[Error] Unable to process.",
            }
            self.message.append(error_message)

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

    def _count_tokens_impl(self, messages):
        try:
            return litellm.token_counter(messages=messages)
        except:
            return self.num_tokens_from_messages(messages)

    def _count_tokens(self, messages):
        try:
            return self._count_tokens_impl(messages)
        except:
            return 0

    def _completion_cost(self, response):
        try:
            return litellm.completion_cost(completion_response=response)
        except:
            return 0.0

    def _completion(self, logger, *args, **kwargs):
        while True:
            try:
                response = litellm.completion(*args, **kwargs)
                cost = self._completion_cost(response)
                logger.debug(f'LLM Cost: {cost}')
                self.cost += cost
                LLMRequestProcessor.total_cost += cost
                return response
            except litellm.RateLimitError:
                logger.error(f'Rate Limit Exceeded. Sleeping for 10 seconds')
                time.sleep(10)
                self.delayed_time += 10
                LLMRequestProcessor.total_delay += 10
            except litellm.ServiceUnavailableError:
                logger.error(f'Service Unavailable. Sleeping for 2 seconds')
                time.sleep(2)
                self.delayed_time += 2
                LLMRequestProcessor.total_delay += 2
            except litellm.APIError:
                logger.error(f'API Error. Sleeping for 5 seconds')
                time.sleep(5)
                self.delayed_time += 5
                LLMRequestProcessor.total_delay += 5
            except litellm.Timeout:
                logger.error(f'Timeout Error. Sleeping for 5 seconds')
                time.sleep(5)
                self.delayed_time += 5
                LLMRequestProcessor.total_delay += 5
            except litellm.ContextWindowExceededError:
                logger.error(f'ContextWindowExceeded')
                self.message.pop(0)

    def _process_request_without_tools(self, role, message: str, logger) -> str:
        self._add_message(role, message)

        response = self._completion(logger,
                                    model=self.model.name,
                                    base_url=self.litellm_url,
                                    api_key=self.litellm_key,
                                    messages=self.message,
                                    custom_llm_provider=self.model.provider)

        returned_message = response.choices[0].message
        response_content = returned_message.content
        self._add_returned_message(returned_message)

        return response_content

    def _process_request_with_tools(self, role, message: str, logger) -> str:
        self._add_message(role, message)

        while True:
            response = self._completion(logger,
                                        model=self.model.name,
                                        base_url=self.litellm_url,
                                        api_key=self.litellm_key,
                                        messages=self.message,
                                        tools=self.tools,
                                        tool_choice="auto",
                                        custom_llm_provider=self.model.provider)

            response_message = response.choices[0].message
            self._add_returned_message(response_message)
            tool_calls = response.choices[0].message.get('tool_calls', [])

            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name

                    if function_name not in self.funcs:
                        logger.error(f'Function {function_name} is not in {self.funcs}')
                        self._add_tool_message(tool_call.id, function_name, f'Function {function_name} not found')
                        continue

                    function_to_call = self.funcs[function_name]
                    function_args = json.loads(tool_call.function.arguments)

                    expected_args = inspect.signature(function_to_call).parameters
                    wrong_arguments = False
                    wrong_arguments_message = ""
                    for arg in function_args:
                        if arg not in expected_args:
                            wrong_arguments = True
                            wrong_arguments_message += f"Argument {arg} not in {expected_args}"

                    if wrong_arguments:
                        logger.error(wrong_arguments_message)
                        self._add_tool_message(tool_call.id, function_name, wrong_arguments_message)
                        continue

                    function_response = function_to_call(
                        **function_args
                    )
                    logger.debug(f'Called function {function_name} with arguments {function_args}')
                    self._add_tool_message(tool_call.id, function_name, function_response)
            else:
                response_content = response_message.content
                return response_content

    def process_request(self, role, message: str, logger) -> str:
        if len(self.tools) == 0:
            return self._process_request_without_tools(role, message, logger)
        return self._process_request_with_tools(role, message, logger)
