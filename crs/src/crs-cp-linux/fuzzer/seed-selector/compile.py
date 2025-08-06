#!/usr/bin/env python3

import os
import argparse
from multiprocessing import Pool

parser = argparse.ArgumentParser()
parser.add_argument("--src-dir", help="target dir having target sources", required=True)
parser.add_argument("--out-dir", help="output dir", required=True)
args = parser.parse_args()
target = args.src_dir
outdir = args.out_dir

def compile(fname):
		code = target + fname
		out = outdir + fname.replace(".c","")
		os.system(f"gcc {code} -o {out}")

targets = os.listdir(target)
with Pool(os.cpu_count()) as p:
  p.map(compile, targets)
