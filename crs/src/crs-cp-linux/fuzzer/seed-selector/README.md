# Seed selector

Seed selector extracts and stores inputs from the Syzbot dashboard,
and builds an index that maps from function names to inputs.

## What it does

Seed selector downloads [a coverage
page](https://storage.googleapis.com/syzbot-assets/39beaee54cd1/ci-qemu-upstream-7367539a.html
) which contains information such as inputs that currently running
Syzkaller has collect, and which input executes which basic blocks,
etc.

Seed selector parses the html file to extract inputs and build a map
from function names to inputs that run a given function.

After running Seed selector, you will see an index like
```
"packet_poll": [
    "14b84b4d94aaf4e5aef858bec2e14853bed88145",
    "3e426e8c06b690e765dd9d7ac9683c5f3909a13e",
    "a546cff56a9789fd53bafa69502ae2330a924ca0"
],
```
where each hash value is a file name of a single input stored in the `raw_corpus` directory.

In addition, seed selector translates inputs written in Syzlang into C
files. For example, if the filename of the syzlang input is
`14b84b4d94aaf4e5aef858bec2e14853bed88145`, the C file name will be
`14b84b4d94aaf4e5aef858bec2e14853bed88145.c`.

## How to setup

Installing necessary packages in the virtual environment

```
python -m venv venv
source ./venv/bin/activate
pip3 install -r ./requirements.txt
```

## How to extract the Syzkaller's corpus

Running the seed selector to extract inputs from the Syzbot dashboard.
```
./seed-selector.py --build-index --outdir=./tmp/
```

If the `--outdir` option is not given, the default value will be `/tmp`.

CAVEAT: when extracting inputs, seed selector by default translates syzlang
inputs to C files using `syz-prog2c`, which is very slow (it takes a
few hours). If you don't want the translation,
you can provide the `--no-want-c-files` option as follows:
```
./seed-selector.py --build-index --outdir=./tmp/ --no-want-c-files
```

It will take 10~15 minutes, and the size of outputs is about 350MB.

## How to select inputs that touch given functions

Suppose `changes.json` is given as follows
```
{
    "426d4a428a9c6aa89f366d1867fae55b4ebd6b7f": {
        "files": [
            "net/tipc/crypto.c"
        ],
        "funcs": [
            "tipc_crypto_key_rcv",
            "tipc_crypto_start"
        ]
    },
    "5bcc3b4468f8d4493b9d0407296ec5a38ecd799e": {
        "files": [
            "net/ipv6/icmp.c"
        ],
        "funcs": [
            "is_ineligible"
        ]
    }
}
```

In changes.json, each entry is a key-value pair from a Linux's commit
to lists of files and functions that the commit changed.

Then, in order to figure out inputs that touch the functions listed in
changes.json (eg, `tipc_crypto_key_rcv`, `tipc_crypto_start`, and
`is_ineligible`), run seed selector as follows:

```
seed-selector --changes=changes.json --outdir=tmp/
```
where the `--outdir` option should be given as the one used in extracting inputs.

Then, `tmp/output.txt` will look like as follows:

```
f2f31cb1eb419d92986b012e7a40cdc29e90a778.c
95878abb936ec5eb639c12ac4c7a6677dc4e2def.c
87006b2fd3bdaebed2d6fc64b5f40835dec498b3.c
```

If you want inputs written in Syzlang instead of C files, run seed selector as follows:
```
seed-select --changes=changes.jon --outdir=tmp/ --no-want-c-files
```

Then, `tmp/output.txt` will look like as follows:
```
f2f31cb1eb419d92986b012e7a40cdc29e90a778
95878abb936ec5eb639c12ac4c7a6677dc4e2def
87006b2fd3bdaebed2d6fc64b5f40835dec498b3
```
