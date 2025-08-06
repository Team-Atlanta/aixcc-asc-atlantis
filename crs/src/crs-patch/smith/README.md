# Smith: A patch system based on LLM

## Environment
- Python 3.11
- Ubuntu 20.04

## Installation
1. Clone the repository.
```bash
$ git clone git@github.com:Team-Atlanta/smith.git
$ git submodule update --init --recursive
```

2. Create your `.env` file in the root directory of the project. You can use `.env.example` as a template.

3. Create a virtual environment and install the required packages.
```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ pip install -r smith/lib/aider/requirements.txt
```

## Usage (exemplar)
```bash
python3 -m smith.main -t 3rd/challenge-001-exemplar -r requests/challenge-001-exemplar.toml --engine gpt-4-turbo-preview --num_samples 5 --fl-top-k 10
python3 -m smith.main -t 3rd/cp-linux-exemplar -r requests/cp-linux-exemplar-CROMU-00001.toml -e gpt-4-turbo-preview -n 5
```

## Notes on exemplar
- Default engine `gpt-3-turbo` doesn't work for `challenge-001-exemplar` due to the short context window size.
- `--fl-top-k 10` is necessary since current bug localizer iterates all hunks of the BIC.

## Usage (benchmark)
```bash
$ python3 -m smith/benchmark -o CADET_00001 --engine gpt-4-turbo-preview -t ./3rd/benchmark/c/cfe/CADET_00001
```

## Testing
- Running tests
```python
pytest tests/test_patcher.py
```

- Writing tests
1. Write test code in `tests/test_patcher.py`
2. Run the test with the environment variable `GENERATE=1`
3. Confirm that the test passes without the environment variable

## Benchmark
Currently, we support the following benchmarks:
- `cp-linux`: Linux kernel vulnerabilities.
- `benchmark/c/cfe`: C programs from Cyber Grand Challenge.
- `benchmark/java/VUL4J-*`: Java programs from VUL4J.
- `bugscpp`: C++ programs from BugsCPP.
