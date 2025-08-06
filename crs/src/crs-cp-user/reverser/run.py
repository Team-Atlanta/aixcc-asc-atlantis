#!/usr/bin/env python3

# for prototype we want to suppress all messages, including those from modules
import warnings
warnings.filterwarnings("ignore")

from argparse import ArgumentParser

from module.reverser import OpenAIWrapper, run_reverser

if __name__ == "__main__":
    parser = ArgumentParser(
        description='Infer the input format of test harness'
    )
    default_model = 'claude-3-opus'
    get_chat = lambda: get_new_model(default_model)
    models = ['claude-3-haiku', 'claude-3-sonnet', 'claude-3-opus', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o']
    challenges = ['linux', 'userspace']

    parser.add_argument('--workdir', help='Working directory')
    parser.add_argument('--target', help='Path to target test harness')
    parser.add_argument('--output', help='Path to output testlang')
    parser.add_argument('--model', choices=models, default=default_model, help='LLM model to use')
    parser.add_argument('--majority', choices=list(range(1, 20)), default=9, type=int, help='Number of agents in majority voting')
    parser.add_argument('--few-shot', action='store_true', help='Use few-shot prompting')
    parser.add_argument('--few-shot-ratio', default=1.0, type=float, help='Ratio of examples to use for few-shot prompt')
    parser.add_argument('--challenge', default='linux', choices=challenges, help='Challenge project')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose information printed')
    parser.set_defaults(func=run_reverser)

    args = parser.parse_args()
    ret = args.func(args)
    # Need to check after parsing b/c we don't want these opts to be mandatory for subcommands
    if (args.func == run_reverser and
        not args.workdir and
        not args.target and
        not args.model and
        not args.majority and
        not args.output):
        parser.error()


    if args.func != run_reverser or args.verbose:
        if type(ret) == str:
            print(ret)
        print(f"${float(OpenAIWrapper.total_cost):.10f}")
