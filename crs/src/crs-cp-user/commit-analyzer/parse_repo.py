import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.commit_parser import CommitParser
from collections import defaultdict
from src.projparser import ProjectParser

import argparse
import json


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="""
Repository parser
                                    
This script parses the repository and outputs the changed files and functions in each commit.
Changes out of the function scope are not considered (e.g., structure definition and global variables).
Only .c and .h files are considered for the analysis.
                                     
Options:
  -t, --target   Specify the path to the target repository.
  -o, --output   Specify the file path to save the results.

Example usage:
  python script.py -t /path/to/repo -o /path/to/output""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--target",
        type=str,
        help="The target repo path to be analyzed",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="The directory to output the results",
        required=True,
    )
    return parser.parse_args()


def parse_repo(target_dir):
    results = defaultdict(lambda: defaultdict(dict))

    project_parser = ProjectParser(target_dir)
    repo_info = project_parser.get_repo_info()

    for subdir, ref in repo_info:
        target_path = os.path.join(target_dir, "src", subdir)
        parse_results = CommitParser(target_path, ref).parse_repo(analyze_unit="commit")

        for commit_changes in parse_results:
            for commit_change in commit_changes:
                files = set()
                funcs = set()

                commit = commit_change.commit_id
                for function_change in commit_change.function_changes:
                    files.add(function_change.after_file)
                    funcs.add(function_change.function_name)

                    results[subdir][commit]["files"] = list(files)
                    results[subdir][commit]["funcs"] = list(funcs)

    return results


def main():
    args = parse_arguments()
    target_dir = args.target
    output_path = args.output

    results = parse_repo(target_dir)

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    main()
