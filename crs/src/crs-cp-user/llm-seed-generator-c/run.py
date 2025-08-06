from llm_seed_gen.llm_seed_generator import LLMSeedGenerator

import argparse
import logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--src_repo_path', type=str, required=True, help='The source repository path')
    parser.add_argument('--test_harness', type=str, required=True, help='The path to test harness file')
    parser.add_argument('--commit_analyzer_output', type=str, required=True, help='The path to output file of commit analyzer')

    parser.add_argument('--nblobs', type=str, required=True, help='Number of blobs to create per commit-sanitizer pair')
    parser.add_argument('--output_dir', type=str, required=True, help='Path to the output directory')
    parser.add_argument('--workdir', type=str, required=True, help='Path to the work directory')

    args = parser.parse_args()

    LLMSeedGenerator(args.src_repo_path, args.test_harness, args.commit_analyzer_output, args.nblobs, 'prompts', 'logs', args.workdir, args.output_dir, logging.DEBUG).run()
