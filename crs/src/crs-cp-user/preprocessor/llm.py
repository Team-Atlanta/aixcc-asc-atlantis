import json
import os
import sys
import traceback
from datetime import datetime
from typing import Callable, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from argparse import ArgumentParser
import asyncio
import sys

from dotenv import load_dotenv
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
import openai
from collections import Counter
from litellm import token_counter, completion_cost

load_dotenv()
LITELLM_URL = os.getenv("LITELLM_URL")
LITELLM_KEY = os.getenv("LITELLM_KEY")
os.environ["OPENAI_API_KEY"] = LITELLM_KEY
os.environ["ANTHROPIC_API_KEY"] = LITELLM_KEY
os.environ['TOKENIZERS_PARALLELISM'] = 'true'
log_file = os.environ.get('LOG_FILE')

THIS_PATH = Path(os.path.abspath(os.path.dirname(__file__)))

# https://docs.litellm.ai/docs/providers/anthropic
LITELLM_MODEL_MAP = {
    'claude-3-haiku': 'claude-3-haiku-20240307',
    'claude-3-sonnet': 'claude-3-sonnet-20240229',
    'claude-3-opus': 'claude-3-opus-20240229',
    'oai-gpt-4o': 'gpt-4o',
    'oai-gpt-4-turbo': 'gpt-4',
    'oai-gpt-4': 'gpt-4',
    'oai-gpt-3.5-turbo': 'gpt-3.5-turbo'
}

MAX_PROMPT_TOKENS = {
    'oai-gpt-3.5-turbo': 16385,
    'oai-gpt-4': 8192,
    'oai-gpt-4-turbo': 128000,
    'oai-gpt-4o': 128000,
    'claude-3-haiku': 200000,
    'claude-3-sonnet': 200000,
    'claude-3-opus': 200000,
}

COMPLETION_TOKENS = 4096

class OpenAIWrapper():
    total_cost = 0.0
    
    def __init__(self, model):
        LITELLM_URL = os.getenv("LITELLM_URL")
        LITELLM_KEY = os.getenv("LITELLM_KEY")
        os.environ["OPENAI_API_KEY"] = LITELLM_KEY
        os.environ["ANTHROPIC_API_KEY"] = LITELLM_KEY
        self.model = model
        self.chat = openai.OpenAI(base_url=LITELLM_URL)
        self.cost = 0.0

    def invoke(self, messages):
        # print(self.model)
        max_tries = 4
        save_error = None
        response = self.chat.chat.completions.create(model=self.model, messages=messages, max_tokens=COMPLETION_TOKENS)
        response_obj = response.choices[0].message
        msg_str = '\n'.join([m['content'] for m in messages])
        # comp_cost = completion_cost(model=LITELLM_MODEL_MAP[self.model], prompt=msg_str, completion=response_obj.content)
        # self.cost += comp_cost
        # OpenAIWrapper.total_cost += comp_cost

        if log_file:
            with open(log_file, 'a') as file:
                json.dump({'messages': messages, 'response': response_obj.content, 'model': self.model, 'cost': comp_cost}, file)
                file.write('\n')

        return response_obj

    def get_num_tokens_from_messages(self, messages):
        return token_counter(model=self.model, messages=messages)
