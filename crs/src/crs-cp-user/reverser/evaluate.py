#!/usr/bin/env python3

from pathlib import Path
import sys
import subprocess
import os
from tools.parser import read_into_test_lang, check_semantics
from tools.test_lang import parse_test_lang, rename_command
from tools.normalize_test_lang import normalizer
from tools.subset import subset_checker
from tools.unwrapper import unwrapper
from zipfile import ZipFile
import datetime
from time import sleep

def unwrap_shenanigans(harness):
    classic_test_lang = parse_test_lang(harness)
    classic_test_lang = unwrapper(classic_test_lang)()
    classic_test_lang = normalizer(classic_test_lang)()
    return classic_test_lang

def check_difference(one, two):
    one, two = open(one).read(), open(two).read()
    one_tl, two_tl = map(unwrap_shenanigans, [one, two])
    one, two = (str(one), str(two))
    # print(one)
    # print(two)
    (one, e1), (two, e2) = read_into_test_lang(one), read_into_test_lang(two)
    if e1 or e2:
        print(e1)
        print(e2)
        return
    
    for gen in [one, two]:
        e = check_semantics(gen)
        if e:
            print(e)
            return

    one, two = one.to_tree(), two.to_tree()
    return one == two, one.distance(two), subset_checker.testlang_is_subset(one_tl, two_tl)

def main():
    harness_dir = sys.argv[1]
    answers_dir = sys.argv[2]
    num_tries = 1

    print('harness             ,  err count,  avg. time,  avg. cost,  avg. dist,  num equal, num subset')

    glob = Path(harness_dir).glob('*.c')
    # handpicked = ['CROMU-00001']
    # glob = [Path(harness_dir) / f'{x}.c' for x in handpicked]
    # options = "--majority 5 --few-shot --few-shot-ratio 0.3"
    options = "--majority 1 -v"
    # options = "--majority 9 --few-shot --few-shot-ratio 1.0 --model claude-3-haiku"
    output_files = []

    time = datetime.datetime.now().isoformat()
    log_file = os.path.abspath(f'./workdir/log-{time}.json')
    with open(log_file, 'w+'):
        pass

    for harness in glob:
        error_count = 0
        times = []
        distances = []
        equal_count = 0
        subset_count = 0
        total_cost = 0.0
        
        for i in range(num_tries):
            output_file = f'./workdir/{harness.stem}_{i}.testlang'
            output_files.append(output_file)
            command = f'LOG_FILE="{log_file}" time -f %e ./run.py --workdir ./workdir --target {harness} --output {output_file} {options}; exit 0'
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            if b'Command' in output:
                error_count += 1
            else:
                times.append(float(output.decode().splitlines()[-1]))
                for line in output.splitlines():
                    if line.startswith(b'$'):
                        total_cost += float(line[1:])
                if (Path(answers_dir) / f'{harness.stem}-ext.txt').is_file():
                    answer_path = Path(answers_dir) / f'{harness.stem}-ext.txt'
                else:
                    answer_path = Path(answers_dir) / f'{harness.stem}.txt'
                equal, distance, subset = check_difference(output_file, answer_path)
                equal_count += 1 if equal else 0
                subset_count += 1 if subset else 0
                distances.append(distance)
        
        avg_time = (sum(times) / len(times)) if len(times) else 999
        avg_dist = (sum(distances) / len(distances)) if len(distances) else 999
        avg_cost = total_cost / num_tries if num_tries else 0
        
        print(f'{harness.stem:20s}, {error_count:10d}, {avg_time:10.5f}, {avg_cost:10.5f}, {avg_dist:10.5f}, {equal_count:10d}, {subset_count:10d}')

        # Hopefully helps with rate limit
        sleep(3)
    
    with ZipFile(f'./workdir/evaluation-{time}.zip', 'w') as output_zip:
        for file in output_files:
            output_zip.write(file)

if __name__ == "__main__":
    main()
    
