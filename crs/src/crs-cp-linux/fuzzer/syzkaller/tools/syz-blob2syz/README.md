# Syz-blob2syz

This tool translates a given datablob into a syzlang input that a
given harness can run.

## How to build

In the Syzkaller directory, run
```
make blob2syz
```

## How to run

`syz-blob2syz` takes two arguments, a path to a datablob and pseudo
syscalls for the harness that will run the datablob.

A datablob can be given in two ways. If you have a single datablob to
run, you can provide it via `-datablob FILE`. If you have multiple
datablobs in a directory, you can provide them via `-blob-dir DIR`
where `DIR` is the path of the directory.

Pseudo syscalls can be given as a format of a syzlang template. You
can specify the syzlang template via `-syzlang FILE` where `FILE` is
the path of a syzlang template (eg,
`sys/linux/harness_linux_test_harness.txt`).

For example, to translate a datablob for the harness that is provided
 by AIxCC (ie, challenge-001-exemplar), we can run the following
 command:

```
syz-blob2syz -datablob=path/to/sample_solve.bin -syzlang sys/linux/harness_linux_test_harness.txt"
```

where `sample_solve.bin` is a datablob stored in the
`exemplar_only/blobs` directory of the `cp-linux-exemplar` repo.

You can see the output as follows:

```
syz_harness$linux_test_harness_cmd1(&(0x7f0000000000)={0x1, 0x1e, 0x5, 0x10, 0x44, "03010000400001800d0001007564703a55445031000000002c00048014000100020017e67f000001000000000000000014000200020017e6e40012670000000000000000"}, 0x58)
syz_harness$linux_test_harness_cmd0(&(0x7f0000000080)={0x0, 0x18, 0x0, "5ad000180000000000000000112233440000126700000003"}, 0x24)
syz_harness$linux_test_harness_cmd0(&(0x7f00000000c0)={0x0, 0x38, 0x0, "4f40003820000000000080001122334400000001c4d40000112233447f000001000000000dac00005544503100"/56}, 0x44)
[SKIPPED]
```

In addition to check the result through stdout, you can store the
result into `corpus.db`, where the path of `corpus.db` is inferred
from the Syzkaller's config.

For example, you can run `syz-blob2syz`, similar to the above, to specify the Syzkaller's config as follows:
```
syz-blob2syz -datablob=path/to/sample_solve.bin -syzlang sys/linux/harness_linux_test_harness.txt -syz-conf SYZCONF"
```
where `SYZCONF` is the path of the Sykzaller's config which specifies the path of the workdir.

Then, outputs will be merged into the corpus (ie,
`path/to/workdir/corpus.db`) if the corpus exists, or the corpus will
be created if it does not exist. With the challenge-001-exemplar
datablob (ie, the one which has the name of `sample_solve.bin` in the
`cp-linux-exemplar` repo), you can check that `corpus.db` contains the
output by running

```
syz-db unpack corpus.db inputs
```

Then, you can see that the `inputs` directory contains a file named
`557d01e6c94e31289343d5aaae7a10ef06ffa693`.

Note that storeing outputs into the corpus relies on `syz-db`. So the
path fo `syz-db` should be appended in the environment variable
`PATH`.

If you want to run type-1 harnesses (ie,
`sys/linux/harness_type2_CADET_00001.txt`), you can either specify the
type of the harness using the `-type` option (eg, `-type="type1"`) or
just run without specifying the harness type. If not specified,
syz-blob2syz first assumes that the harness type is type-2, and if it
fails, it again tries to parse datablob by assuming the type-1
harness.


## TODO

1. Make the tool more robust. There are many corner cases to handle,
   so the tool needs more tests and work.

