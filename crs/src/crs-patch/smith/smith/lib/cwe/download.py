#!/usr/bin/env python3

import subprocess
import os
import csv

def load_cwes(pn):
    rtn = []
    for line in open(pn, "rt"):
        line = line.strip()
        if len(line) == 0:
            continue
        cwe, _desc = line.split(":")
        assert cwe.startswith("CWE-")
        rtn.append(int(cwe[4:]))
    return rtn

def load_cwes_from_csv(pn):
    with open(pn, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader) # skip header
        for row in reader:
            yield int(row[0])

def main():
    # for cwe in load_cwes("./CWE.md"):
    for cwe in load_cwes_from_csv("./cwe-software.csv"):
        url = f"https://cwe.mitre.org/data/definitions/{cwe}.html"
        if os.path.exists(f"raw/CWE-{cwe}.txt"):
            print(f"[!] Skip {url}")
        else:
            print(f"[!] Downloading: {url}")
            result = subprocess.run(
                ["w3m", "-dump", "-cols", "200", url],
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                text = True,
                check=True
            )
            with open(f"raw/CWE-{cwe}.txt", "w") as fd:
                fd.write(result.stdout)

        if os.path.exists(f"summary/CWE-{cwe}.txt"):
            print(f"[!] Skip summarizing: {url}")
        else:
            print(f"[!] Summarizing: {url}")
            subprocess.run(
                [f"./summarize.py raw/CWE-{cwe}.txt summary/CWE-{cwe}.txt"],
                shell=True, check=True)

if __name__ == '__main__':
    main()
