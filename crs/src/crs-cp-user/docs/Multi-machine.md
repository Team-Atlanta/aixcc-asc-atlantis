# Architecture

```
node1: verifier (vapi), patch, dind1, iapi (submission system interface)
node2: crs-cp-user (+ dind2), crs-cp-linux, crs-cp-jenkins
node3: crs-cp-user (+ dind3), crs-cp-linux, crs-cp-jenkins
```

- `crs_scratch` is NFS, shared file system
- `cp_root` is read-only

# CRS scratch files

change runner workdir back to root, do sth else for output of things

it's called `runner.build_dir`

Commit analyzer
- event lock
- parse lock
- changes json
- candidates json

CRSAGI
- lock
- runner dict dir
- runner seeds dir

CP
- under CP base, so ok

# CRS structure

- Runner
    - workdir is not shared (on root), but is configurable at initialization
    - CP
    - [x] Commit_Analyzer, uses `runner.workdir`
        - `event`
        - `parse` (event)
    - SeedsGen uses `hrunner.workdir`, subdir of `runner.workdir`
        - `event`
        - on a per-harness basis, **ignore**
    - [ ] Project_Analyzer
        - returns path to results, which are not shared
        - `dicts_event`
        - `corpus_event`
    - [x] CRSAGI
        - has fixed output dir for results, `runner.seeds_dir` which is set to
          `/assets/...`, should move to `crs_scratch`
        - `event`

    - Libfuzzer
        - CrashCollector
        - HarnessRunner (through method parameter)
        - CP (through hrunner clone project)
    - LibAFL
    - Hybrid
    - HarnessRunner in `async_run`

Pay attention to
```
parse_changes = asyncio.create_task(self.commit_analyzer.parse_changes(self))
commit_analyze = asyncio.create_task(self.commit_analyzer.async_run(self))
get_oss_corpus = asyncio.create_task(self.proj_analyzer.get_oss_corpus(self))
get_oss_dicts = asyncio.create_task(self.proj_analyzer.get_oss_dicts(self))
crs_agi = asyncio.create_task(self.crs_agi.async_get_dict(self))
```

# Testing workflow

```
sudo mount --bind crs-cp-user crs-mount

# Prepare multi src
./run-docker.sh cp-mock-multi-src
# TODO test for the single source version

# In one terminal window
export CRS_USER_NODE=0
export CRS_USER_CNT=2
cd crs-cp-user
DEBUG=1 python3 run.py --cp 'Mock CP'

# In another window
export CRS_USER_NODE=1
export CRS_USER_CNT=2
cd crs-mount
DEBUG=1 python3 run.py --cp 'Mock CP'
```

# (old notes) Build synchronization

Need to use file locks (or similar) in `crs_scratch`.
- Runner
  - project clone into itself, RO version
- HarnessRunner
  - project clone for each harness
- How long to hold file lock?
- If trying to acquire build lock, we are blocked, then after obtaining it we assume build has finished?

Synchronize the tasks of the machines? One CRS has a set of tasks that don't conflict w/ the other?
- Less synchronization needed, meaning less overhead
- But we have less fine-grain control over resources, e.g. give more CPUs to LibAFL instead of Libfuzzer
- Let one machine build libfuzzer, the other libafl\_libfuzzer.
- Let one machine only run libfuzzer (not sure how to distribute it).
  For libafl, can look into syncing it

# Fuzzing

- Is the fuzzing in CP Docker done inside each dind? 
- Can the fuzzing processes communicate through `crs_scratch`, e.g. socket file?

# CPU allocation

If testing on local via bind mount, slash total CPU for each machine in half (?) and offset one.
Can synchronize this number at startup.
