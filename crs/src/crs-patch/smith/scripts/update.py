#!/usr/bin/env python3
# pylint: disable=all
# type: ignore

import argparse
import os
import sys

SMITH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(SMITH, 'cp-linux', 'CVEs', 'bin'))

from benchmark import *


CI_HEADER = """
name: Benchmark CI

on:
  workflow_dispatch:
  schedule:
    - cron: 0 0 * * 0

defaults:
  run:
    working-directory: smith

jobs:
  Init:
    runs-on: cp-linux
    steps:
      - run: git pull --recurse-submodules
      - run: git reset --hard ${{ github.sha }}
"""

def update_CI(benchmarks):
    cves = []
    samples = []
    for b in benchmarks:
        if b.is_cve: cves.append(f"./cp-linux/CVEs/{b.name}")
        else: samples.append(f"./cp-linux/samples/{b.name}")
    cves = sorted(cves)
    samples = sorted(samples)
    ci = CI_HEADER
    for target in cves:  # No samples yet
        name = os.path.basename(target)
        ci += f"  {name}:\n"
        ci +=  "    needs: Init\n"
        ci +=  "    runs-on: cp-linux\n"
        ci +=  "    steps:\n"
        ci += f"      - run: ./cp-linux/CVEs/bin/build.sh {target}\n"
        ci += f"      - run: ./cp-linux/CVEs/bin/check.py --target {target}\n"
        ci +=  "      - env:\n"
        ci +=  "          OPENAI_API_KEY: ${{ secrets.KAIST_OPENAI_API_KEY }}\n"
        ci += f"        run: python3 main.py -t {target} -e gpt-4-1106-preview -n 10\n"
    ci = ci.strip()
    with open(f"{SMITH}/.github/workflows/benchmark.yml", "wt") as f:
        f.write(ci)

def main():
    benchmarks = get_benchmarks()
    return update_CI(benchmarks)

if __name__ == '__main__':
    main()
