import math
import random
from pathlib import Path
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.prompts import (ChatPromptTemplate, HumanMessagePromptTemplate, FewShotChatMessagePromptTemplate)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from rapidfuzz import fuzz

PROMPT_DIR = Path(__file__).parent.parent / 'prompts'
HARNESS_DIR = Path(__file__).parent.parent / 'test_harnesses'
ANSWERS_DIR = Path(__file__).parent.parent / 'answers'

def load_file(fname):
    with open(fname, "rt") as f: return f.read()

def few_shot_example(harness, answer):
    return f'''Test harness:
<harness>
{harness}
</harness>
Testlang:
<testlang>
{answer}
</testlang>'''

def few_shot_suffix(harness):
    return f'''Test harness:
<harness>
{harness}
</harness>
Testlang:'''

    
def few_shot_harnesses(original_harness, few_shot_ratio):
    few_shot_ratio = max(0.01, few_shot_ratio)
    few_shot_ratio = min(1.0, few_shot_ratio)
    examples = []
    harnesses = list(HARNESS_DIR.glob('*.c'))
    k = math.ceil(few_shot_ratio * len(harnesses))
    k = min(len(harnesses), k) # floating point arithmetic paranoia
    print(f'Few shot with {k} examples')
    chosen = random.choices(harnesses, k=k)
    for harness_file in chosen:
        current_code = load_file(harness_file)
        ratio = fuzz.ratio(original_harness, current_code)
        if ratio > 90:
            continue
        basename = harness_file.stem
        base_ver = ANSWERS_DIR / f'{basename}.txt'
        ext_ver = ANSWERS_DIR / f'{basename}-ext.txt'
        if ext_ver.is_file():
            answer = load_file(ext_ver)
        elif base_ver.is_file():
            answer = load_file(base_ver)
        else:
            continue
        examples.append(few_shot_example(current_code, answer))
    prompt = '\n'.join(examples)
    return prompt


def final_prompt_reverse_linux(harness, additional_prompt, args, original_harness=None):
    if original_harness is None:
        original_harness = harness
    system = {'role': 'system', 'content': load_file(PROMPT_DIR / 'SYSTEM')}
    instructions = {'role': 'user', 'content': load_file(PROMPT_DIR / 'PROMPT')}
    constant_array = {'role': 'user', 'content': load_file(PROMPT_DIR / 'CONSTANT_ARRAY')}
    string = {'role': 'user', 'content': load_file(PROMPT_DIR / 'STRING')}
    suffix = {'role': 'user', 'content': few_shot_suffix(harness)}
    ret = [
        system,
        instructions,
        constant_array,
        string,
    ]
    if args.few_shot:
        few_shot = {'role': 'user', 'content': few_shot_harnesses(original_harness, args.few_shot_ratio)}
        ret.append(few_shot)
    ret.append(suffix)
    if additional_prompt is not None:
        ret.append({'role': 'user', 'content': additional_prompt})
    return ret

def final_prompt_reverse_userspace(harness, additional_prompt, args, original_harness=None):
    if original_harness is None:
        original_harness = harness
    system = {'role': 'system', 'content': load_file(PROMPT_DIR / 'SYSTEM')}
    instructions = {'role': 'user', 'content': load_file(PROMPT_DIR / 'USERSPACE')}
    grammar = {'role': 'user', 'content': load_file(PROMPT_DIR / 'GRAMMAR')}
    ascii_ = {'role': 'user', 'content': load_file(PROMPT_DIR / 'ASCII')}
    suffix = {'role': 'user', 'content': few_shot_suffix(harness)}
    ret = [
        system,
        instructions,
        grammar,
        ascii_,
        suffix,
    ]
    if additional_prompt is not None:
        ret.append({'role': 'user', 'content': additional_prompt})
    return ret

def final_prompt_reverse(harness, additional_prompt, args, original_harness=None):
    if args.challenge == 'userspace':
        return final_prompt_reverse_userspace(harness, additional_prompt, args, original_harness=original_harness)
    # Default to Linux CP
    return final_prompt_reverse_linux(harness, additional_prompt, args, original_harness=original_harness)

if __name__ == '__main__':
    pass
