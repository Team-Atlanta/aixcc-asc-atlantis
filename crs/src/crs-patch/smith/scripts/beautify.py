#!/usr/bin/env python3

import argparse
import json
import os

def parse_args():
    parser = argparse.ArgumentParser(description='Beautify a raw_prompt.json file')
    parser.add_argument('--output_dir', '-o', type=str, help='Path to the output directory')
    parser.add_argument('file', type=str, help='Path to the raw_prompt.json file')
    return parser.parse_args()

def main():
    args = parse_args()
    if not args.file.endswith('.json'):
        print('File must be a JSON file')
        return

    print(f'Beautifying {args.file}')

    if os.path.exists(args.output_dir):
        print(f'Output directory {args.output_dir} already exists. Exiting...')
        return

    os.makedirs(args.output_dir)

    with open(args.file, 'r') as f:
        raw_prompt = json.loads(f.read())

    for i, chat in enumerate(raw_prompt):
        role =  chat['role']
        path = f'{args.output_dir}/{i:02}_{role}.txt'
        with open(path, 'w') as f:
            f.write(chat['content'])

if __name__ == '__main__':
    main()
