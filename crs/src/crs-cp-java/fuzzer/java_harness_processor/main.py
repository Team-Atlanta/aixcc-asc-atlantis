import os
import argparse
from harness.utils.logger import Log
from harness.processor import java_processing, llm_processing

def parse_args():
    parser = argparse.ArgumentParser(description='Harness Processor')
    parser.add_argument('project', type=str, help='project directory')
    parser.add_argument('harnessid', type=str, help='harnessid in project.yaml')
    parser.add_argument('-p', '--processor', type=str, help='processor to use', default='llm', choices=['java', 'llm'])
    parser.add_argument('-f', '--format', type=str, help='output harness format', default='composite', choices=['composite', 'jazzer', 'protobuf', 'concolic'])
    parser.add_argument('-o', '--output_dir', type=str, help='output directory', default='.')
    parser.add_argument('--include-origin', help='include original code in a generated harness', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode', default=False)
    return parser.parse_args()

args = parse_args()

if args.verbose:
    Log.level = 'debug'

def main():
    if args.processor == 'java':
        java_processing(args)
    elif args.processor == 'llm':
        llm_processing(args)

if __name__ == '__main__':
    main()