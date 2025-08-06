#!/usr/bin/env python3

# for prototype we want to suppress all messages, including those from modules
import warnings
warnings.filterwarnings("ignore")

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
from tools.parser import read_into_test_lang, check_semantics
from tools.hash_equivalence import is_equivalent
from tools.test_lang import parse_test_lang, rename_command
from tools.prompting import final_prompt_reverse
from tools.resolve_preprocessor import preprocessor_pass, switch_case_constant_patch, strip_comments
from tools.normalize_test_lang import normalizer, nondata_field_remover
from tools.unwrapper import unwrapper
from tools.subset import subset_checker

from dotenv import load_dotenv
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
import openai
from collections import Counter
from litellm import token_counter, completion_cost

from math import log2

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
        self.model = model
        self.chat = openai.AsyncOpenAI(base_url=LITELLM_URL)
        self.cost = 0.0

    async def invoke(self, messages):
        print(self.model)
        max_tries = 4
        save_error = None
        for i in range(max_tries):
            try:
                response = await self.chat.chat.completions.create(model=self.model, messages=messages, max_tokens=COMPLETION_TOKENS)
                break
            except openai.RateLimitError as e:
                save_error = e
                print('Rate limit error, sleeping and trying again')
                await asyncio.sleep(2 ** (i + 3)) # start with 8 second wait
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                save_error = e
                print('API connection error, sleeping and trying again')
                await asyncio.sleep(2 ** (i + 3)) # start with 8 second wait
        else:
            raise save_error
        response_obj = response.choices[0].message
        msg_str = '\n'.join([m['content'] for m in messages])

        if log_file:
            with open(log_file, 'a') as file:
                json.dump({'messages': messages, 'response': response_obj.content, 'model': self.model, 'cost': comp_cost}, file)
                file.write('\n')

        return response_obj

    def get_num_tokens_from_messages(self, messages):
        return 0
        # return token_counter(model=self.model, messages=messages)

class Suppressor():
    def __enter__(self):
        self.stdout = sys.stdout
        sys.stdout = self
        self.stderr = sys.stderr
        sys.stderr = self

    def __exit__(self, exception_type, value, traceback):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        if exception_type is not None:
            # Silently exit with code 1
            sys.exit(1)

    def write(self, x): pass

    def flush(self): pass

def get_new_model(model, verbose=False):
    return OpenAIWrapper(model)

def load_prompt(fname):
    with open(THIS_PATH / fname, "rt") as f:
        return {'role': 'user', 'content': f.read()}

def load_file(fname):
    with open(fname, "rt") as f: return f.read()

def remove_markdown(data):
    return data.replace('```', '').strip()

def isolate_code_helper(response, start, end):
    response = response.replace(', type: data', '')
    in_code = False
    build = []
    for line in response.split('\n'):
        if line.startswith(start):
            in_code = True
            continue
        elif line.startswith(end):
            in_code = False
            continue
        if in_code:
            build.append(line)
    if len(build) > 0:
        return '\n'.join(build)
    return response

def isolate_markdown_code(response):
    response = isolate_code_helper(response, '```', '```')
    return response

def isolate_xml_code(response):
    response = isolate_code_helper(response, '<testlang>', '</testlang>')
    return response

def parse_error(data):
    lang, error = read_into_test_lang(data)
    if error:
        print(data)
        return error

    return check_semantics(lang)

async def resolve_errors(harness_src_path, chat, few_shot, few_shot_ratio, result, msgs=None) -> Union[str, None]:
    if msgs is None:
        msgs = []

    error = parse_error(isolate_xml_code(result))
    max_iteration = 5
    i = 0
    while error is not None:
        if i >= max_iteration:
            result = None
            break
        msg = "While parsing, the following error was found, could you please resolve the error?\n"
        msg += str(error) + '\n'
        msg += 'If you are completely unable to resolve this error or if you have tried 5 times, start again from scratch.\n'
        msg += "Please only give the updated input format, you believe represents the input format.\n"
        msg += "As before, DO NOT provide any commentary on your work."

        result = await reverse_test_harness_once(harness_src_path, chat, msg, few_shot, few_shot_ratio)
        error = parse_error(result)
        i += 1
    print(f'resolved after {i} iterations')

    return result

async def find_relevant_harness_code(harness_code: str) -> str:
    iterations = 0
    start = 0
    end = -1
    while iterations < 3:
        try:
            reconstruct = []
            for (i, line) in enumerate(harness_code.splitlines()):
                new_line = f'/* {i+1} */ {line}'
                reconstruct.append(new_line)
            # TODO reduce few shot prompt first
            # TODO use another model, maybe Haiku? gpt-3.5-turbo's ctx window isn't actually that large
            chat = get_new_model('oai-gpt-3.5-turbo')
            msgs = [load_prompt('prompts/REDUCE'), '\n'.join(reconstruct)]
            r = await chat.invoke(msgs)
            j = json.loads(r.content)
            start = j['start'] - 1
            end = j['end'] - 1
            break
        except:
            iterations += 1
    return '\n'.join(harness_code.splitlines()[start:end])

# TODO could encapsulate harness_path, chat, few_shot, few_shot_ratio into a struct
async def reverse_test_harness_once(harness_src_path, chat, additional_prompt, few_shot, few_shot_ratio):
    harness_code = load_file(harness_src_path)
    # replace switch-case values with constants from IR
    harness_code = switch_case_constant_patch(harness_code)
    # clang -E pass
    harness_code = preprocessor_pass('harness', harness_code)
    original_harness = harness_code
    final_prompt = final_prompt_reverse(harness_code, additional_prompt, few_shot, few_shot_ratio)
    while True:
        num_tokens = chat.get_num_tokens_from_messages(final_prompt)
        print(f'Prompt tokens: {num_tokens}')
        if num_tokens + COMPLETION_TOKENS < MAX_PROMPT_TOKENS[chat.model]:
            break
        harness_code = await find_relevant_harness_code(harness_code)
        final_prompt = final_prompt_reverse(harness_code, additional_prompt, few_shot, few_shot_ratio, original_harness=original_harness)
    r = await chat.invoke(final_prompt)
    print('skib', r)
    return isolate_xml_code(r.content)

async def reverse_test_harness(harness_src_path, chat, few_shot=False, few_shot_ratio=1.0):
    try:
        response = await reverse_test_harness_once(harness_src_path, chat, None, few_shot, few_shot_ratio)
        r = await resolve_errors(harness_src_path, chat, few_shot, few_shot_ratio, response)
    except Exception as e:
        print(e)
        r = None

    print('sus', r)
    return r

async def generate_n_harnesses(harness_path: str, n: int, chat: OpenAIWrapper, few_shot, few_shot_ratio) -> List[str]:
    calls = []
    for _ in range(n):
        calls.append(asyncio.create_task(reverse_test_harness(harness_path, chat, few_shot, few_shot_ratio)))
    generated = await asyncio.gather(*calls)
    print('returning')
    return [h for h in generated if h is not None]

def basic_wrapped_reverse(args):
    return asyncio.run(reverse_test_harness_once(args.harness_path, get_chat(), None, False, 1.0))

def majority(harness_src_path, n, chat, few_shot=False, few_shot_ratio=1.0) -> Optional[str]:
    generated = asyncio.run(generate_n_harnesses(harness_src_path, n, chat, few_shot, few_shot_ratio))
    print(generated)
    if not generated:
        return load_file(Path(__file__).parent / 'answers/fallback.txt')
    unique_harnesses = []
    transformed_harnesses = []
    group_to_unique = {}
    harness_to_lang = {}
    harness_counters = [0] * n
    for new_harness in generated:
        test_lang, error = read_into_test_lang(new_harness)
        if error:
            continue
        try:
            classic_test_lang = parse_test_lang(new_harness)
            transformed_test_lang = unwrapper(classic_test_lang)()
            transformed_test_lang = normalizer(transformed_test_lang)()
            transformed_harness = str(transformed_test_lang)
            print(transformed_harness)
        except:
            print('Majority: parsing error!')
            continue
        for (j, u) in enumerate(transformed_harnesses):
            if harness_to_lang[u] == test_lang:
                harness_counters[j] += 1
                break;
        else:
            harness_counters[len(unique_harnesses)] = 1
            unique_harnesses.append(new_harness)
            transformed_harnesses.append(transformed_harness)
            harness_to_lang[transformed_harness] = test_lang
        for group in group_to_unique.keys():
            group_test_lang = parse_test_lang(group)
            group_test_lang = unwrapper(group_test_lang)()
            group_test_lang = normalizer(group_test_lang)()
            if subset_checker.testlang_is_subset(group_test_lang, transformed_test_lang):
                group_to_unique[group].append(new_harness)
                break
            elif subset_checker.testlang_is_subset(transformed_test_lang, group_test_lang):
                uniques = group_to_unique.pop(group)
                uniques.append(new_harness)
                group_to_unique[str(classic_test_lang)] = uniques
                break
        else:
            group_to_unique[str(classic_test_lang)] = [new_harness]
    # max() throws ValueError if iterable is empty, but this shouldn't happen if LLM + error loop?
    max_count = max(harness_counters)
    max_idx = harness_counters.index(max_count)
    print(f'Length of unique {len(unique_harnesses)}, Length of groupings {len(group_to_unique)}, Max count {max_count}, Max idx {max_idx}')
    ret =  unique_harnesses[max_idx]
    print('Returned harness is part of following grouping ==============================')
    for (group, uniques) in group_to_unique.items():
        if ret in uniques:
            print(group)
            break
    print('=============================================================================')
    # If popular won by at least max(2, ratio * n) then return
    if max_count >= max(2, 0.5 * len(generated)):
        return ret
    # Else find most popular group and return. TODO maybe return most popular in group is exists?
    try:
        max_group_len = max([len(uniques) for uniques in group_to_unique.values()])
        group = next(g for (g, u) in group_to_unique.items() if len(u) == max_group_len and max_group_len > 1)
        return group
    except:
        # Otherwise return ret, i.e. the first generated
        return ret

def main_logic(args):
    # resolve paths
    inpath = Path(args.target).resolve()
    outpath = Path(args.output).resolve()
    # cd to working dir
    os.chdir(args.workdir)
    chat = get_new_model(args.model)
    # get generated grammar
    result = majority(inpath, args.majority, chat, args.few_shot, args.few_shot_ratio)
    # parse test lang and rename it
    testlang = parse_test_lang(result)
    testlang = rename_command(testlang)
    # write to output
    with open(outpath, 'w') as f:
        f.write(str(testlang))
    return str(testlang)

# args must have workdir, target, output fields
def main_command(args):
    if args.verbose:
        tl = main_logic(args)
        print(tl)
        answer_path = Path(__file__).parent / f'answers/{Path(args.target).stem}.txt'
        answer_path_ext = Path(__file__).parent / f'answers/{Path(args.target).stem}-ext.txt'
        the_path = None
        if answer_path_ext.is_file():
            the_path = answer_path_ext
        elif answer_path.is_file():
            the_path = answer_path
        if the_path:
            tl_tl = parse_test_lang(tl)
            tl_tl = unwrapper(tl_tl)()
            tl_tl = normalizer(tl_tl)()
            a_tl = parse_test_lang(load_file(the_path))
            a_tl = unwrapper(a_tl)()
            a_tl = normalizer(a_tl)()
            success = is_equivalent(str(tl_tl), str(a_tl))
            print(f'Is equivalent to {the_path}? {success}')
            success = subset_checker.testlang_is_subset(tl_tl, a_tl)
            print(f'Are the annotations a subset of {the_path}? {success}')
            success = subset_checker.testlang_is_subset(a_tl, tl_tl)
            print(f'Are the annotations a superset (overconfident) of {the_path}? {success}')
    else:
        # suppress all stdout/stderr, including those from libs
        with Suppressor():
            main_logic(args)

if __name__ == "__main__":
    parser = ArgumentParser(
        description='Infer the input format of test harness'
    )
    default_model = 'oai-gpt-4o'
    get_chat = lambda: get_new_model(default_model)
    models = ['claude-3-haiku', 'claude-3-sonnet', 'claude-3-opus', 'oai-gpt-3.5-turbo', 'oai-gpt-4', 'oai-gpt-4-turbo', 'oai-gpt-4o']

    parser.add_argument('--workdir', help='Working directory')
    parser.add_argument('--target', help='Path to target test harness')
    parser.add_argument('--output', help='Path to output testlang')
    parser.add_argument('--model', choices=models, default=default_model, help='LLM model to use')
    parser.add_argument('--majority', choices=list(range(1, 20)), default=9, type=int, help='Number of agents in majority voting')
    parser.add_argument('--few-shot', action='store_true', help='Use few-shot prompting')
    parser.add_argument('--few-shot-ratio', default=1.0, type=float, help='Ratio of examples to use for few-shot prompt')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose information printed')
    parser.set_defaults(func=main_command)

    args = parser.parse_args()
    ret = args.func(args)
    # Need to check after parsing b/c we don't want these opts to be mandatory for subcommands
    if (args.func == main_command and
        not args.workdir and
        not args.target and
        not args.model and
        not args.majority and
        not args.output):
        parser.error()


    if args.func != main_command or args.verbose:
        if type(ret) == str:
            print(ret)
        print(f"${float(OpenAIWrapper.total_cost):.10f}")
