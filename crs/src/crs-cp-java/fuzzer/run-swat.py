#!/usr/bin/env python3

import argparse
import os
import random
import socket
import contextlib
import subprocess
import tempfile

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
    swat_path = args.swat
    print(f'SWAT PATH: {swat_path}')
    harness_class = args.harness_class
    print(f'harness_class: {harness_class}')
    harness_directory = f'{args.harness_directory}/{harness_class}'
    print(f'harness_directory: {harness_directory}')

    fuzzing_directory = f'{args.harness_directory}/fuzz/{harness_class}'
    print(f'Fuzzing directory: {fuzzing_directory}')

    fuzzing_corpus_path = f'{fuzzing_directory}/corpus_dir'
    print(f'fuzzing_corpus_path: {fuzzing_corpus_path}')

    tempname = next(tempfile._get_candidate_names())
    concolic_instance_name = f'concolic-{harness_class}-{tempname}'

    concolic_corpus_path = f'{fuzzing_directory}/{concolic_instance_name}'
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
    cmd += ["-c", f'{harness_class}_Concolic']
    cmd += ["-l", f'{concolic_log_path}']
    cmd += ["-v", f'{sym_var}']
    cmd += ["-f", f'{fuzzing_corpus_path}']
    cmd += ["-C", f'{concolic_corpus_path}']
    cmd += ["--prioritize-concolic"]
    cmd += ["--port", f'{port}']
    cmd += ["-p", f'{class_path}']
    if args.no_swat_output:
        cmd += ["-n"]

    subprocess.run(cmd)

def main():
    args = parse_args()
    run_concolic(args)

if __name__ == '__main__':
    main()
