# Harness Preprocessor
```
Preprocessor finds C files to be analyzed by other modules (i.e. reverser)
```

# Usage
```
usage: preprocessor.py [-h] --workdir WORKDIR --target TARGET --source SOURCE --output OUTPUT

Find C entrypoint and other relevant code

options:
  -h, --help         show this help message and exit
  --workdir WORKDIR  Working directory
  --target TARGET    Path to target test harness
  --source SOURCE    Path to source code
  --output OUTPUT    Path to output response
```

Example
```
python3 preprocessor.py --workdir /crs-workdir --target /mock-cp/src/test/stdin_harness.sh --source /mock-cp-src --output /crs-workdir/mock-cp.out
```
This writes C code to the file at `--output` which can be analyzed by the `reverser` module.

# apt deps
- tree
- pip
- python3
