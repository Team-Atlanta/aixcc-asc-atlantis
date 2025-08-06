# How to use the script to fuzz cp-linux challenges (Contact Jiho for questions)

## Setup
Please ensure that Go is installed. Version is important. The script is tested with version 1.21.8.
There are multiple ways to install Go, with Snap making it easier.
```
snap install go --channel=1.21/stable --classic
```

## Usage (scripts/run.py)
```
./scripts/run.py config [-h] [--build] [--force] [--extract] [--debug] [--verbose] [--http [HTTP]]
```

`config`: yaml config file

`--build`: build syzkaller without running (make generate, make)

`--clear`: remove syzlang files listed in the config

`--nokvm`: run qemu without kvm

#### Options are for debugging, may not be used in competition

`--extract`: run make extract also (use with --build)

`--force`: force copy linux source for build without reusing existing one (use with --build, when linux source is updated)

`--debug`: run syzkaller with --debug

`--verbose`: run syzkaller as verbose

`--http` `IP:Port`: run syzkaller's http server and bind to port (default `0.0.0.0:56741`)

## Config File

Config file should be written in YAML.

#### Required configs

`linux`: Linux kernel source path (should be built already)

`harness`: Target harness binary path

`img`: Filesystem image file path. (ex. bookworm.img, then bookworm.img.id_rsa is also needed)

`syscall`: list of target pseudo-syscalls

#### Optional Configs
`harness_id`: harness ID (ex. CROMU-00005), if not given, the name of harness binary will be used.

`verifier`: path to verifier (`verifier --harness harness_id --pov blobfile` will be executed)

`syzlang`: list of syzlang files (.txt and .txt.const)

`filter`: list of target files / functions to give more weight in KCOV (with regex). Give weight x5 for files, x15 for functions.

`filter_deny`: list of files to be ignored in KCOV (with regex)

`vm_count`: Number of VM instances

`core`: Number of cores for each VM instance

`procs`: Number of parallel fuzzing processes in each VM instance

`workdir`: custom workdir path for syzkaller (default: workdir-harness/[harness name])


Example
```KPRCA-00001.yaml
linux: "/home/hahah/aixcc/cp-linux-exemplar/src"
harness: "/home/hahah/aixcc/cp-linux-exemplar/out/KPRCA-00001"
harness_id: KPRCA-00001
img: "9p"
syscall:
  - "syz_harness_type2$kprca_00001*"
sanitizers:
  id_1: 'KASAN: slab-out-of-bounds'
  id_2: 'KASAN: stack-out-of-bounds'
  id_3: 'KASAN: use-after-free'
  id_4: 'KASAN: null-ptr-deref'
  id_5: 'KASAN: global-out-of-bounds'
  id_6: 'UBSAN: array-index-out-of-bounds'

# optionals
syzlang:
  - "/home/hahah/aixcc/CRS-cp-linux/fuzzer/syzkaller/workdir-test/harness_KPRCA_00001.txt"
  - "/home/hahah/aixcc/CRS-cp-linux/fuzzer/syzkaller/workdir-test/harness_KPRCA_00001.txt.const"
filter:
  files:
    - "^drivers/KPRCA-00001"
  functions:
    - "^handle_main$"
filter_deny:
  - "^fs/exec.c"
  - "^kernel/fork.c"
  - "^kernel/pid.c"
  - "^lib/maple_tree.c"
  - "^net/9p/"
  - "^fs/9p/"
vm_count: 1
core: 4
procs: 6
```

Build / Run
```
./scripts/run.py KPRCA-00001.yaml --build # for build
./scripts/run.py KPRCA-00001.yaml # for run
```


## Extracting blobs from db

Currently, it is inefficient. (SyzProg -> C prog -> Compile -> Run (only blob generation w/o harness))

Takes few seconds.

SyzProgs with type_1 harness may produce multiple blobs

```
$WORKDIR/bin/syz-db -os=linux -arch=amd64 unpack-blobs $CORPUS_DB $TARGET_DIR
```
`-os` and `-arch` is optional (linux/amd64 is default)


Example
```
$ ./bin/syz-db unpack-blobs work/corpus.db ./blobs
$ ls blobs
1d8082c84d3f22fc0c1fe0d9989d8cecde812a13  61d0a0c8ef1f3652842fd70f78a6901394aeb202  9282b665656c99971794421621a4d9ef1a69c0c2
1e952564726e8a98e03823f27e0b9f3396811be4  7825d60b00f2f0df6338d303e2ffe9c6636fa1a8  98f8c16e7b70efa256973ea11f0489a261e9b353
4a6692fd9d8644500ee1a895b7d860c8a15496e5  80b94fde5982bc1198d14f0a84ed684e6fa8e31a  af2b94f35d2a43b0013bc9ba491932e72d453648
5268c9a16abd521c1b50ad3ce7a295f3fc88feee  817c9a39d1f600a767020ed6862a5244b7eb741b  d144e4cb82dd34ae8292dc0449d73ae214cda8c5
601919346077139cf0386c0cb8676583f9fe9e77  8c05e46f4c54a0ca0f861183b411956e30e529d4  e983c249e3548cd4375b2e327de2bafcf8471b84
$ ls blobs/1d8082c84d3f22fc0c1fe0d9989d8cecde812a13
blob_00000842234279374674
```


## Using harness executor

Prepare syzlang files for harness. functions should start with `syz_harness$`, and be defined for each command.

Example [CVE-2022-0995](/fuzzer/syzkaller/sys/linux/harness_cve_2022_0995.txt)
```
syz_harness$cve_2022_0995_cmd0(buf ptr[in, harness_cve_2022_0995_cmd0], len bytesize[buf])
syz_harness$cve_2022_0995_cmd1(buf ptr[in, harness_cve_2022_0995_cmd1], len bytesize[buf])

harness_cve_2022_0995_cmd0 {
	opcode	int32[0]
	size	flags[watch_queue_size, int32]
} [packed]

harness_cve_2022_0995_cmd1 {
	opcode	int32[1]
	size	bytesize[data, int32]
	data	watch_notification_filter
} [packed]
```

Build syzkaller and harness_executor binary:
```
make extract TARGETOS=linux SOURCEDIR=$KSRC
make generate
make
make harness_executor
```

Add config options for harness files.

Example (see `init_files`, `init_cmds`, `harness_executor`)
```
{
  "target": "linux/amd64",
  "http": "0.0.0.0:56741",
  "workdir": "/home/hahah/aixcc/syz-workdir/cve-2022-0995/work",
  "kernel_obj": "/home/hahah/aixcc/cp-linux-exemplar/src",
  "kernel_src": "/home/hahah/aixcc/cp-linux-exemplar/src",
  "init_files": ["/home/hahah/aixcc/cp-linux-exemplar/out/CVE-2022-0995"],
  "init_cmds": ["mv /CVE-2022-0995 /harness; chmod +x /harness; ls -al /harness*"],
  "image": "/home/hahah/aixcc/cp-linux/assets/bookworm.img",
  "sshkey": "/home/hahah/aixcc/cp-linux/assets/bookworm.img.id_rsa",
  "syzkaller": "/home/hahah/aixcc/CRS-cp-linux/fuzzer/syzkaller",
  "procs": 6,
  "enable_syscalls": [ "syz_harness$cve_2022_0995_*" ],
  "type": "qemu",
  "vm": {
    "count": 1,
    "kernel": "/home/hahah/aixcc/cp-linux-exemplar/src/arch/x86/boot/bzImage",
    "cmdline": "net.ifnames=0 nokaslr",
    "cpu": 2,
    "mem": 2048
  },
  "harness_executor": "default"
}
```
