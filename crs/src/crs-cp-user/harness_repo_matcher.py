import argparse
import yaml
import os
import re


def parse_project_yaml(yaml_file):
    parsed_data = yaml.safe_load(open(yaml_file))
    return parsed_data


def get_src_repository_paths(parsed_data, cp_repo_path):
    cp_srcs = parsed_data['cp_sources']
    cp_src_repo_paths = []

    for _dir in cp_srcs:
        cp_src_repo_path = os.path.join(cp_repo_path, f'src/{_dir}')
        cp_src_repo_paths.append(cp_src_repo_path)

    return cp_src_repo_paths


def extract_includes(harness_file):
    with open(harness_file, 'r') as file:
        lines = file.readlines()

    uncommented_includes = []
    inside_multiline_comment = False

    for line in lines:
        # Remove inline comments
        line = re.sub(r'//.*', '', line)

        # Check for multiline comments
        if '/*' in line:
            inside_multiline_comment = True
        if '*/' in line:
            inside_multiline_comment = False
            continue

        # If inside a multiline comment, skip the line
        if inside_multiline_comment:
            continue

        # Find uncommented includes
        match = re.match(r'^\s*#\s*include\s*<[^>]+>|^\s*#\s*include\s*"[^"]+"', line)
        if match:
            uncommented_includes.append(line.strip())

    return uncommented_includes


def starts_with_path(abs_path_1, abs_path_2):
    abs_path_1 = os.path.normpath(abs_path_1)
    abs_path_2 = os.path.normpath(abs_path_2)

    common_path = os.path.commonpath([abs_path_1, abs_path_2])

    return common_path == abs_path_2


standard_headers = {
    "assert.h", "complex.h", "ctype.h", "errno.h", "fenv.h", "float.h",
    "inttypes.h", "iso646.h", "limits.h", "locale.h", "math.h", "setjmp.h",
    "signal.h", "stdarg.h", "stdbool.h", "stddef.h", "stdint.h", "stdio.h",
    "stdlib.h", "string.h", "tgmath.h", "time.h", "wchar.h", "wctype.h"
}


def use_include_to_match_repo(harness_file, cp_src_repo_paths):
    scores = {}

    includes = extract_includes(harness_file)

    for include in includes:
        pattern = r'"(.*?)"'
        relative_path_to_src = re.findall(pattern, include)

        if len(relative_path_to_src) != 1:
            continue

        src_path = os.path.join(os.path.dirname(harness_file), relative_path_to_src[0])
        src_abs_path = os.path.abspath(src_path)

        for src_repo_path in cp_src_repo_paths:
            if starts_with_path(src_abs_path, src_repo_path):
                if src_repo_path not in scores:
                    scores[src_repo_path] = 1
                else:
                    scores[src_repo_path] += 1

    for include in includes:
        pattern = r'<(.*?)>'
        header_tokens = re.findall(pattern, include)

        if len(header_tokens) != 1:
            continue

        if header_tokens[0] in standard_headers:
            continue

        for src_repo_path in cp_src_repo_paths:
            for dirpath, dirnames, filenames in os.walk(src_repo_path):
                for filename in filenames:
                    if ".h" not in filename:
                        continue
                    header_path = os.path.abspath(os.path.join(dirpath, filename))
                    if header_tokens[0] in header_path:
                        if src_repo_path not in scores:
                            scores[src_repo_path] = 1
                        else:
                            scores[src_repo_path] += 1
    if not scores:
        return None

    return max(scores, key=scores.get)


def get_matching_src_repo(yaml_file, harness_file):
    # Use absolute path
    yaml_file = os.path.abspath(yaml_file)
    harness_file = os.path.abspath(harness_file)
    cp_repo_path = os.path.dirname(yaml_file)

    # Parse project.yaml
    parsed_data = parse_project_yaml(yaml_file)
    # Get list of src repo paths
    cp_src_repo_paths = get_src_repository_paths(parsed_data, cp_repo_path)

    result = use_include_to_match_repo(harness_file, cp_src_repo_paths)

    if result is not None:
        return result

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--project_yaml_file', type=str, required=True, help='The project.yaml file')
    parser.add_argument('--test_harness_file', type=str, required=True, help='The test harness file')

    args = parser.parse_args()

    print(get_matching_src_repo(args.project_yaml_file, args.test_harness_file))
