#!/usr/bin/env python3

import argparse
import base64
import contextlib
import glob
import json
import os
import random
import signal
import socket
import subprocess
import sys
import tempfile
import time


def parse_args():
    parser = argparse.ArgumentParser(description='Concolic Executor Wrapper for Jazzer')
    parser.add_argument('-s', '--swat',
                        type=str, help='SWAT directory')

    parser.add_argument('-H', '--harness-directory',
                        type=str,
                        help='Harness Directory (/crs_scratch/java/harnesses/jenkins')
    parser.add_argument('-c', '--harness-class',
                        type=str, help='harness class')
    parser.add_argument('-l', '--logs',
                        type=str, help='log head directory')

    parser.add_argument('-p', '--class-path',
                        type=str, help='classpath for running SWAT')
    parser.add_argument('-v', '--sym-var',
                        type=str, help='symbolic variable', default='Ljava/lang/String')
    parser.add_argument('-t', '--port',
                        type=str, help='http port')
    parser.add_argument('-n', '--no-swat-output',
                        help='suppress SWAT output', action='store_true', default=False)

    return parser.parse_args()

def find_free_port():
    while True:
        port = random.randint(18000, 19000)
        try:
            with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(('127.0.0.1', port))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                return s.getsockname()[1]
        except:
            pass

def run_concolic(args):

    # get args
    swat_path = args.swat
    print(f'SWAT PATH: {swat_path}')
    harness_class = args.harness_class
    print(f'harness_class: {harness_class}')
    harness_parent_directory = args.harness_directory
    harness_directory = f'{args.harness_directory}/{harness_class}'
    print(f'harness_directory: {harness_directory}')

    # parent/fuzz/class_nameConcolic/concolic-xxxxx will be instance directory (there will be one)
    concolic_fuzzing_parent_directory = f'{harness_parent_directory}/fuzz/{harness_class}'
    print(f'Concolic fuzzing directory: {concolic_fuzzing_parent_directory}')

    # find fuzzers
    while True:
        time.sleep(1)
        orig_class_name = harness_class[0:harness_class.find("_Concolic")]
        _glob_string = f'{harness_parent_directory}/fuzz/{orig_class_name}_*'
        print(f'Finding fuzzers at {_glob_string}')

        # list of fuzzer directories is at fuzzer_dirs
        fuzzer_dirs = [x for x in list(glob.glob(_glob_string)) if not 'Concolic' in x]
        fuzzer_dirs = [x for x in fuzzer_dirs if not '_Fuzz' in x]
        if len(fuzzer_dirs) > 0:
            break

    # list of fuzzer directories is at fuzzer_dirs
    print(f'Fuzzers at {" ".join(fuzzer_dirs)}', file=sys.stderr)
    j = json.dumps(fuzzer_dirs)
    fuzzer_dirs_json_base64 = str(base64.b64encode(bytes(j, 'utf-8')), 'utf-8')
    print(fuzzer_dirs_json_base64)

    #fuzzing_corpus_path = f'{fuzzing_directory}/corpus_dir'
    #print(f'fuzzing_corpus_path: {fuzzing_corpus_path}')

    # create a concolic instance name
    #tempname = next(tempfile._get_candidate_names())
    # fix an instance name for ASC
    tempname = 'instance'
    concolic_instance_name = f'{harness_class}-{tempname}'

    concolic_corpus_path = f'{concolic_fuzzing_parent_directory}/{concolic_instance_name}'
    print(f'concolic_corpus_path: {concolic_corpus_path}')

    swat_concolic_script = f'{swat_path}/scripts/concolic-fuzzing.py'
    print(f'swat_concolic_script: {swat_concolic_script}')

    class_path = args.class_path
    sym_var = args.sym_var

    print(f'concolic_instance_name: {concolic_instance_name}')

    log_head_path = args.logs
    concolic_log_path = f'{log_head_path}/{concolic_instance_name}'

    port = find_free_port()
    print(f'port number: {port}')
    print('\n\n\n')

    cmd = [swat_concolic_script]
    cmd += ["-s", f'{swat_path}']
    cmd += ["-c", f'{harness_class}']
    cmd += ["-l", f'{concolic_log_path}']
    cmd += ["-v", f'{sym_var}']
    cmd += ["-f", f'{fuzzer_dirs_json_base64}']
    cmd += ["-C", f'{concolic_corpus_path}']
    cmd += ["--prioritize-concolic"]
    cmd += ["--port", f'{port}']
    cmd += ["-p", f'{class_path}']
    cmd += ["-H", f'{harness_directory}']
    if args.no_swat_output:
        cmd += ["-n"]

    print(' '.join(cmd))
    procs.clear()
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    procs.append(proc)
    proc.wait()


# Cascading SIGUSR1
procs = []

def sigusr1_handler(signum, stack):
    print(f"{__file__} received SIGUSR1 {len(procs)} {procs}")
    for p in procs:
        print(f"{__file__} sending SIGUSR1 to child pid = {p.pid}")
        os.kill(p.pid, signal.SIGUSR1)
    
    for p in procs:
        os.waitpid(p.pid, os.WUNTRACED)
    os._exit(0)

def main():
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    args = parse_args()
    run_concolic(args)

if __name__ == '__main__':
    main()
