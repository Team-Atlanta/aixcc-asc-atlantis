# PoC-Converter

PoC Converter aims to generate acceptable blobs by AIxCC sanitizer systems

PoC Converter utilizes information from `reverser` and `CVE-analyzer` for generating PoV.

Converter module can receive selected seeds from `seed-selector` module to convert it into blob format (if possible).

Converter module emits intermediate outputs for use as syzkaller seeds.


# Setup

```
pip install -r ./requirements.txt
```


# Prepare

```
CRS-cp-linux/fuzzer$ python -m converter.prepare [-h] --bin-dir BIN_DIR --out-dir OUT_DIR --kernel KERNEL [--work-dir WORK_DIR] [--cpus CPUS]

Prepares system call trace in advance

options:
  -h, --help           show this help message and exit
  --bin-dir BIN_DIR    Directory of binaries to prepare traces
  --out-dir OUT_DIR    Output directory
  --kernel KERNEL      Directory of tracer kernel
  --work-dir WORK_DIR  Work directory for tracing
  --cpus CPUS          Max CPU count for parallel tracing
```

# Run

```
CRS-cp-linux/fuzzer$ python -m converter.run [-h] --poc-dir POC_DIR --harness HARNESS --testlang TESTLANG [--prep-dir PREP_DIR] [--proj-def PROJ_DEF] [--work-dir WORK_DIR] [--kasan-kernel KASAN_KERNEL] --no-kasan-kernel NO_KASAN_KERNEL --out-dir OUT_DIR [--out-seed-dir OUT_SEED_DIR] [--cpus CPUS]

Converts PoC system calls into harness compatible blobs

options:
  -h, --help            show this help message and exit
  --poc-dir POC_DIR     Directory of candidate PoC binaries
  --harness HARNESS     Path of harness binary
  --testlang TESTLANG   Path of harness reverse result
  --prep-dir PREP_DIR   Directory of prepared traces
  --proj-def PROJ_DEF   Project definition file
  --work-dir WORK_DIR   Work directory for conversion process
  --kasan-kernel KASAN_KERNEL
                        Directory of KASan enabled kernel
  --no-kasan-kernel NO_KASAN_KERNEL
                        Directory of KASan disabled kernel
  --out-dir OUT_DIR     Output directory for generated PoV
  --out-seed-dir OUT_SEED_DIR
                        Output directory for all generated blobs
  --cpus CPUS           Max number of concurrent conversion sessions
```
