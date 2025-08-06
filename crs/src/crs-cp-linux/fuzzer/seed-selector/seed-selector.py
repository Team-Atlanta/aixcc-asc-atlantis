#!/usr/bin/env python3

"""A simple script to extract the Syzkaller's corpus"""


import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import requests
from bs4 import BeautifulSoup

outdir_env_var = "OUT_DIR"
outdir_global = "/tmp"
outdir = os.environ[outdir_env_var] if outdir_env_var in os.environ else outdir_global


def get_cover_html_from_file(filename):
    with open(filename) as f:
        contents = f.read()
    return contents


def get_url_for_inst(inst):
    # NOTE: getting the url is hard-coded based on the design of the
    # current upstream page. We need to modify this if Syzbot changes
    # the page.
    upstream_url = "https://syzkaller.appspot.com/upstream"
    response = requests.get(upstream_url)
    if response.status_code == 200:
        upstream_page = response.text
    else:
        raise Exception(
            "Failed to retrieve the HTML file. Status={}".format(response.status_code)
        )
    soup = BeautifulSoup(upstream_page, "html.parser")
    for a_elem in soup.find_all("a"):
        if a_elem.get_text() == inst:
            l = a_elem.parent.parent
            a0 = l.find_all("a")[1]
            return a0["href"]

    raise Exception("wrong inst name: {}".format(inst))


def get_cover_html_from_web(inst):
    url = get_url_for_inst(inst)
    print("Retrieving the html page from {}".format(url))
    response = requests.get(url)
    if response.status_code == 200:
        html = response.text
        return html
    else:
        raise Exception(
            "Failed to retrieve the HTML file. Status={}".format(response.status_code)
        )


def get_cover_html(inst, filename):
    """If filename exists, read the file and return it. If not,
    retrieve the html file from the Syzkaller's dashboard"""
    try:
        contents = get_cover_html_from_file(filename)
    except:
        contents = get_cover_html_from_web(inst)
    return contents


def __extract_functions_from_code(code):
    import tempfile

    def is_canonical_line(line):
        return re.match(r"[a-zA-Z0-9_]+\s+[a-z]+\s+[0-9]+", line)

    tmp = tempfile.NamedTemporaryFile()
    fn = os.path.join(outdir, tmp.name)
    with open(fn, "w") as f:
        f.write(code.get_text())
        f.flush()
        cmd = "ctags -x --language-force=C {}".format(fn)
        output = subprocess.getoutput(cmd)

        index_list = []
        lines = output.splitlines()
        for line in lines:
            toks = line.split()
            if len(toks) < 3 or not is_canonical_line(line):
                continue
            name, typ, line = toks[0], toks[1], int(toks[2])
            if typ.find("function") == -1:
                continue
            index_list.append([name, line, 0])
        index_list.sort(key=lambda x: x[1])
        for i in range(len(index_list) - 1):
            index_list[i][2] = index_list[i + 1][1] - 1
    index = {name: values for name, *values in index_list}
    return index


def __build_index_for_funcs(prog_lines, funcs):
    # TODO: Optimize

    # prog_lines().get_text() removes tags that we need such as <span>.
    lines = str(prog_lines).splitlines()
    f = {}
    for func, rnge in funcs.items():
        f0 = set()
        for i in range(rnge[0], rnge[1]):
            line = lines[i]
            if len(line) == 0:
                continue
            s = re.search(r"onProgClick\(([0-9]*?),", line)
            if s:
                prog = "prog_{}".format(s.group(1))
                f0.add(prog)
        if len(f0) != 0:
            f[func] = list(f0)
    return f


def __extract_progs_from_html(soup):
    progs = []
    for prog_elem in soup.find_all("pre", id=re.compile(r"^prog_")):
        prog = prog_elem.get_text()
        id = prog_elem["id"]
        prog = re.sub(r"^$\n", "", prog, flags=re.MULTILINE)
        progs.append((id, prog))
    return progs


def __extract_index_from_html(soup):
    index = {}
    for (contents_elem,) in soup.find_all("pre", id=re.compile(r"^contents_")):
        try:
            tds = contents_elem.find_all("td")
            input_annotation, code = tds[0], tds[2]
            funcs = __extract_functions_from_code(code)
            index.update(__build_index_for_funcs(input_annotation, funcs))
        except:
            print("Failed to parse {}".format(contents_elem["id"]), file=sys.stderr)
    return index


def extract_progs_and_index_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    progs = __extract_progs_from_html(soup)
    index = __extract_index_from_html(soup)
    return progs, index


def hash(data):
    h = hashlib.sha1()
    h.update(data)
    return h.hexdigest()


def save_index(index, idmap, outdir):
    for func in list(index.keys()):
        progs = index[func]
        filtered = filter(lambda x: x in idmap, progs)
        progs = list(map(lambda x: idmap[x], filtered))
        index[func] = progs
        if len(index[func]) == 0:
            del index[func]

    # TODO: Currently, index is stored as a json file. Do we want a
    # better option?
    filename = "index"
    path = os.path.join(outdir, filename)
    with open(path, "w") as f:
        json.dump(index, f, sort_keys=True, indent=4)


def save_raw_corpus(progs, outdir, want_c_files):
    raw_corpus_filename = "dsl"
    raw_corpus_path = os.path.join(outdir, raw_corpus_filename)
    try:
        os.makedirs(raw_corpus_path, exist_ok=True)
    except:
        print(
            "[WARN] {} already exists. Contents may be overwritten".format(
                raw_corpus_filename
            )
        )
    idmap = {}
    for prog0 in progs:
        id, prog = prog0
        hsh = hash(prog.encode("utf-8"))
        idmap[id] = hsh
        path = os.path.join(raw_corpus_path, hsh)
        with open(path, "w") as f:
            f.write(prog)
        if want_c_files:
            may_translate_prog2c([hsh], True, outdir)
    return raw_corpus_path, idmap


def pack_corpus(raw_corpus, outdir):
    import subprocess
    from shutil import which

    syzdb = "syz-db"
    if which(syzdb) is None:
        return

    corpus_filename = "corpus.db"
    corpus_path = os.path.join(outdir, corpus_filename)
    curver = 4
    cmd = [syzdb, "--version={}".format(curver), "pack", raw_corpus, corpus_path]
    subprocess.run(cmd)


def build_index(args):
    html = get_cover_html(args.instance, args.file)

    progs, index = extract_progs_and_index_from_html(html)

    raw_corpus_path, idmap = save_raw_corpus(
        progs, args.outdir, not args.no_want_c_files
    )
    save_index(index, idmap, args.outdir)

    pack_corpus(raw_corpus_path, args.outdir)


def load_index(args):
    index_filename = os.path.join(args.outdir, "index")
    with open(index_filename) as f:
        index = json.load(f)

    return index


no_prog2c_warned = False


def check_prog2c(prog2c):
    global no_prog2c_warned
    if no_prog2c_warned:
        return False

    if shutil.which(prog2c) == None:
        no_prog2c_warned = True
        print(
            "[WARN] {} does not exist. Cannot translate syzlang input to C".format(
                prog2c
            )
        )
        return False

    return True


def may_translate_prog2c(seeds, want_c_files, outdir):
    if not want_c_files:
        return seeds

    prog2c = "syz-prog2c"
    if not check_prog2c(prog2c):
        return seeds

    corpusdir = os.path.join(outdir, "code")
    seedcs = []
    for seed in seeds:
        seedc = seed + ".c"
        seedc_path = os.path.join(corpusdir, seedc)

        if seed.endswith(".c"):
            continue
        if os.path.exists(seedc_path):
            seedcs.append(seedc)
            continue

        seed_path = os.path.join(corpusdir, seed)
        cmd = prog2c + " -prog {}".format(seed_path)
        output = subprocess.getoutput(cmd)
        with open(seedc_path, "w+") as f:
            f.write(output)
        seedcs.append(seedc)

    return seedcs


def lookup_interesting_seeds_for_commit(index, commit, want_c_files, outdir):
    # TODO: The current index format does not contain the names of
    # files in which functions reside. This may cause false positives
    # if the same funtion name is defined in multiple files with the
    # keyword.
    res = []
    funcs_str = "funcs"
    if funcs_str not in commit:
        return res

    for func in commit[funcs_str]:
        if func in index:
            seeds = may_translate_prog2c(index[func], want_c_files, outdir)
            res.extend(seeds)

    return res


def extract_interesting_seeds(args, index):
    outdir = args.outdir
    outfile = args.output
    outpath = os.path.join(outdir, outfile)
    if os.path.exists(outpath):
        print(
            "[WARN] {} already exists. May overwrite it".format(outpath),
            file=sys.stderr,
        )

    want_c_files = not args.no_want_c_files

    with open(args.changes) as f:
        changes_dir = json.load(f)

    seeds = []
    for dir_name in changes_dir:
        changes = changes_dir[dir_name]
        for commit in changes:
            seeds0 = lookup_interesting_seeds_for_commit(
                index, changes[commit], want_c_files, outdir
            )
            seeds.extend(seeds0)

    with open(outpath, "w+") as f:
        f.write("\n".join(seeds))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", action="store", default="ci-qemu-upstream")
    parser.add_argument("--build-index", action="store_true")
    # Arguments for building an index
    parser.add_argument("--file", action="store", default="")
    parser.add_argument("--outdir", action="store", default=outdir)
    # Arguments for extracting interesting seeds
    parser.add_argument("--changes", action="store", default="")
    parser.add_argument("--output", action="store", default="output.txt")
    parser.add_argument("--no-want-c-files", action="store_true")
    args = parser.parse_args()

    try:
        os.makedirs(args.outdir, exist_ok=True)
    except:
        pass

    if args.build_index:
        build_index(args)

    index = load_index(args)

    if len(args.changes) != 0:
        extract_interesting_seeds(args, index)

if __name__ == "__main__":
    main()
