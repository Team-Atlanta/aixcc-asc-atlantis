# LLM Seed Generator

```
The LLM Seed Generator leverages test harness, and git commit information to create test blobs designed to trigger vulnerabilities in CPVS. 
These test blobs also serve as high-quality seeds for fuzzing.
```

## How to setup
```
pip3 install -r requirements.txt
```
- Environment Variables

```
LITELLM_URL=http://bombshell.gtisc.gatech.edu:4000
LITELLM_KEY=sk-KEY
```

## How to Use
- The LLM Seed Generator takes following arguments
```
--src_repo_path: Provide the path to the source repository.
--test_harness: Provide the path to the test harness file.
--commit_analyzer_output: Specify the path to the output file of the commit analyzer.
--nblobs: Indicate the number of blobs to create per commit-sanitizer pair.
--output_dir: Provide the path to the directory where the output blobs will be stored.
--workdir: Provide the path to the work directory.
```
- Example
```
python3 run.py --src_repo_path PATH_TO_SRC_REPO --test_harness PATH_TO_TEST_HARNESS_DIR/filein_harness.c --commit_analyzer_output PATH_TO_COMMIT_ANALYZER_OUTPUT --nblobs 5 --output_dir PATH_TO_OUTPUT_DIR --workdir PATH_TO_WORKDIR
```
- Invalid Inputs
```
Among all the inputs, three critical ones can cause fatal errors: src_repo_path, test_harness and output_dir.
```