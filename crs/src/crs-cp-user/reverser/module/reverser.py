import json
import os
import sys
import traceback
from datetime import datetime
from typing import Callable, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import sys
from copy import copy
from .parser import read_into_test_lang, check_semantics
from .hash_equivalence import is_equivalent
from .test_lang import parse_test_lang, rename_command
from .prompting import final_prompt_reverse
from .resolve_preprocessor import preprocessor_pass, switch_case_constant_patch, strip_comments
from .normalize_test_lang import normalizer, nondata_field_remover
from .unwrapper import unwrapper
from .subset import subset_checker

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

THIS_PATH = Path(os.path.abspath(os.path.dirname(__file__))).parent

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
    
    def __init__(self, model, temperature=None):
        self.model = model
        self.chat = openai.AsyncOpenAI(base_url=LITELLM_URL)
        self.cost = 0.0
        self.temperature = temperature

    async def invoke(self, messages):
        print(self.model)
        max_tries = 4
        save_error = None
        for i in range(max_tries):
            try:
                response = await self.chat.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=COMPLETION_TOKENS,
                    # temperature=self.temperature
                )
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
        # comp_cost = completion_cost(model=LITELLM_MODEL_MAP[self.model], prompt=msg_str, completion=response_obj.content)
        # self.cost += comp_cost
        # OpenAIWrapper.total_cost += comp_cost

        if log_file:
            with open(log_file, 'a') as file:
                json.dump({'messages': messages, 'response': response_obj.content, 'model': self.model}, file)
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

def get_new_model(model, temperature=None, verbose=False):
    # if model in CLAUDE_MODEL_MAP:
    #     model = CLAUDE_MODEL_MAP[model]
    return OpenAIWrapper(model, temperature=temperature)

def load_prompt(fname):
    with open(THIS_PATH / fname, "rt") as f:
        return {'role': 'user', 'content': f.read()}

def load_file(fname):
    with open(fname, "rt") as f: return f.read()

def load_user(content):
    return {'role': 'user', 'content': f'{content}'}

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
        print(error)
        return error

    try:
        classic = lang.get_classic()
        classic.check()
    except SyntaxError as e:
        print('Classic parse error')
        print(data)
        print(str(e))
        return str(e)
    
    return check_semantics(lang)

async def resolve_errors(args, chat, result, msgs=None) -> Union[str, None]:
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
        
        result = await reverse_test_harness_once(args, chat, msg)
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
async def reverse_test_harness_once(args, chat, additional_prompt):
    harness_code = load_file(args.target)
    # replace switch-case values with constants from IR
    harness_code = switch_case_constant_patch(harness_code)
    # clang -E pass
    harness_code = preprocessor_pass('harness', harness_code)
    original_harness = harness_code
    final_prompt = final_prompt_reverse(harness_code, additional_prompt, args)
    while True:
        num_tokens = chat.get_num_tokens_from_messages(final_prompt)
        print(f'Prompt tokens: {num_tokens}')
        if num_tokens + COMPLETION_TOKENS < MAX_PROMPT_TOKENS[chat.model]:
            break
        harness_code = await find_relevant_harness_code(harness_code)
        final_prompt = final_prompt_reverse(harness_code, additional_prompt, args, original_harness=original_harness)
    r = await chat.invoke(final_prompt)
    print('skib', r)
    return isolate_xml_code(r.content)

async def reverse_test_harness(args, chat, additional_prompt=None):
    try:
        response = await reverse_test_harness_once(args, chat, additional_prompt)
        r = await resolve_errors(args, chat, response)
    except Exception as e:
        print(e)
        r = None

    print('sus', r)
    return r

async def generate_n_harnesses(args, chat: OpenAIWrapper, additional_prompt=None, once=False) -> List[str]:
    calls = []
    for _ in range(args.majority):
        if once:
            calls.append(asyncio.create_task(reverse_test_harness_once(args, chat, additional_prompt=additional_prompt)))
        else:
            calls.append(asyncio.create_task(reverse_test_harness(args, chat, additional_prompt=additional_prompt)))
    generated = await asyncio.gather(*calls)
    print('returning')
    return [h for h in generated if h is not None]

def majority(args, chat) -> Optional[str]:
    try:
        generated = asyncio.run(generate_n_harnesses(args, chat))
    except:
        generated = None
#     generated = ['''
#     GLOBALS ::= ITEMS_COUNT { size: 4, value: 3 }

# INPUT ::= ITEM[ITEMS_COUNT]
#           ITEM_INDEX { size: 4 }

# ITEM ::= ITEM_DATA { size: 40, terminator: 10 }
#     ''']
    print(generated)
    if not generated:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')
    # if len(generated)
    unique_harnesses = []
    transformed_harnesses = []
    group_to_unique = {}
    harness_to_lang = {}
    harness_counters = [0] * args.majority
    for new_harness in generated:
        test_lang, error = read_into_test_lang(new_harness)
        if error:
            continue
        try:
            classic_test_lang = test_lang.get_classic()
            transformed_test_lang = normalizer(classic_test_lang)()
            transformed_test_lang = unwrapper(transformed_test_lang)()
            transformed_harness = str(transformed_test_lang)
            print(transformed_harness)
        except Exception:
            print('Majority: parsing error!')
            print(traceback.format_exc())
            continue
        test_lang, error = read_into_test_lang(transformed_harness)
        if error:
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
            group_test_lang, _ = read_into_test_lang(group)
            group_test_lang = group_test_lang.get_classic()
            group_test_lang = normalizer(group_test_lang)()
            group_test_lang = unwrapper(group_test_lang)()
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

def choose_best(args, chat):
    try:
        generated = asyncio.run(generate_n_harnesses(args, chat))
    except:
        generated = None
    if not generated:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')

def best_harness_of_two(harness_src_path, one, two, chat):
    # msgs = [load_prompt("prompts/PROMPT"), load_user(load_file(harness_src_path)), load_user(one), load_user(two), load_prompt("prompts/BESTOFTWO")]
    msg2 = f'''<harness>
{load_file(harness_src_path)}
</harness>

Grammar 1:
<grammar>
{load_user(one)}
</grammar>

Grammar 2:
<grammar>
{load_user(two)}
</grammar>'''
    # msgs = [load_prompt("prompts/BESTOFTWO"), load_user(load_file(harness_src_path)), load_user(one), load_user(two)]
    msgs = [load_prompt("prompts/BESTOFTWO"), load_user(msg2)]
    r = asyncio.run(chat.invoke(msgs))
    
    better_one = r.content[0]
    print(r.content)
    # TODO: occasionally, better_one is not one or two which creates a problem. It should retry and re
    best = one if r.content[0] == '1' else two

    #combination = resolve_errors(chat, r.content[1:], [load_prompt("prompts/PROMPT")])
    #msgs = [load_prompt("prompts/PROMPT"), load_file(harness_src_path), best, combination, load_prompt("prompts/BESTOFTWO")]
    #r = get_new_model().invoke(msgs)
    #better_two = r.content[0]

    return int(better_one) # if better_two == '1' else combination

def best_harness_of_two_consensus(harness_src_path, one, two, voters, chat):
    best_choice, _ = Counter([best_harness_of_two(harness_src_path, one, two, chat) for _ in range(voters)]).most_common(1)[0]
    return best_choice

def best_of_n(args, chat):
    harness_src_path = args.target
    # n = ((args.majority + 1) // 2) * 2
    n = args.majority
    voters = 3
    # candidates = list(reverse_test_harness(harness_src_path, chat) for _ in range(n))
    try:
        candidates = asyncio.run(generate_n_harnesses(args, chat))
    except:
        candidates = None
    if not candidates:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')

    chat = get_new_model('oai-gpt-4o')
    print('Candidates')
    for candidate in candidates:
        print(candidate, '\n\n')

    for _ in range(int(log2(n))):
        new_candidates = list()
        for i in range(0, len(candidates), 2):
            if i + 1 >= len(candidates):
                best = 1
            else:
                best = best_harness_of_two_consensus(harness_src_path, candidates[i], candidates[i + 1], voters, chat)
                best2 = best_harness_of_two_consensus(harness_src_path, candidates[i + 1], candidates[i], voters, chat)
                print(best == best2)
            # print(candidates[i + best - 1])
            new_candidates.append(candidates[i + best - 1])
        candidates = new_candidates
    
    return candidates[0]

def regenerate(args, chat):
    fast_args = copy(args)
    fast_args.model = 'oai-gpt-4o'
    # fast_args.model = 'claude-3-haiku'
    fast_args.majority = 6
    fast_chat = get_new_model(fast_args.model, temperature=2)
    try:
        generated = asyncio.run(generate_n_harnesses(fast_args, fast_chat, once=True))
    except:
        generated = None
    if not generated:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')

    smart_args = copy(args)
    smart_args.model = 'claude-3-opus'
    smart_args.majority = 3
    smart_chat = get_new_model(smart_args.model, temperature=2)
    try:
        generated_smart = asyncio.run(generate_n_harnesses(smart_args, smart_chat, once=True))
    except:
        generated_smart = None
    if not generated:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')
    generated += generated_smart

    additional_prompt = 'Previous attempts, analyze the best features, rationalize, and generate an accurate testlang that represents the harness\'s input\n'''
    for g in generated:
        additional_prompt += f'<testlang>\n{g}\n</testlang>\n'
    print(additional_prompt)

    intermediate_args = copy(args)
    intermediate_args.model = 'claude-3-opus'
    intermediate_args.majority = 3
    intermediate_chat = get_new_model(intermediate_args.model, temperature=2)
    try:
        generated2 = asyncio.run(generate_n_harnesses(intermediate_args, intermediate_chat, additional_prompt=additional_prompt))
    except:
        generated2 = None
    if not generated2:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')

    additional_prompt = 'Previous attempts that may not be well-formatted.\n'''
    for g in generated:
        additional_prompt += f'<testlang>\n{g}\n</testlang>\n'
    additional_prompt += '\nSmarter attempts, analyze the best features, rationalize, and generate an accurate testlang that represents the harness\'s input\n'''
    for g in generated2:
        additional_prompt += f'<testlang>\n{g}\n</testlang>\n'
    print(additional_prompt)

    try:
        grammar = asyncio.run(reverse_test_harness(args, chat, additional_prompt=additional_prompt))
    except:
        grammar = None
    if not grammar:
        return load_file(Path(__file__).parent.parent / 'answers/fallback.txt')
    return grammar
    
def main_logic(args):
    # resolve paths
    args.target = Path(args.target).resolve()
    args.output = Path(args.output).resolve()
    # cd to working dir
    os.chdir(args.workdir)
    chat = get_new_model(args.model)
    # get generated grammar
    if args.challenge == 'userspace':
        result = regenerate(args, chat)
    else:
        result = majority(args, chat)
    # parse test lang and rename it
    testlang = parse_test_lang(result)
    testlang = rename_command(testlang)
    # write to output
    with open(args.output, 'w') as f:
        f.write(str(testlang))
    return str(testlang)
        
# args must have workdir, target, output fields
def run_reverser(args):
    if args.verbose:
        tl = main_logic(args)
        print(tl)
        answer_path = Path(__file__).parent.parent / f'answers/{Path(args.target).stem}.txt'
        answer_path_ext = Path(__file__).parent.parent / f'answers/{Path(args.target).stem}-ext.txt'
        the_path = None
        if answer_path_ext.is_file():
            the_path = answer_path_ext
        elif answer_path.is_file():
            the_path = answer_path
        if the_path:
            tl_tl = parse_test_lang(tl)
            tl_tl = normalizer(tl_tl)()
            tl_tl = unwrapper(tl_tl)()
            a_tl = parse_test_lang(load_file(the_path))
            a_tl = normalizer(a_tl)()
            a_tl = unwrapper(a_tl)()
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
