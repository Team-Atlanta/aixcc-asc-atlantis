# syzlang-gen

Generates syzlang for drivers using SyzDescribe + LLM.

# usage
```
usage: main.py [-h] --source_base SOURCE_BASE --driver_path DRIVER_PATH [--workdir WORKDIR] --output_file OUTPUT_FILE
               [--copy_source] [--num_cores NUM_CORES] [--kernel_version KERNEL_VERSION]

Process source_base and driver_path.

options:
  -h, --help            show this help message and exit
  --source_base SOURCE_BASE
                        Path to the source base directory
  --driver_path DRIVER_PATH
                        Path to the driver directory
  --workdir WORKDIR     Path to the working directory (default: current directory)
  --output_file OUTPUT_FILE
                        Path to the output file
  --copy_source         Copy Linux source to local workdir
  --num_cores NUM_CORES
                        Number of cores to use while building
```

For `--copy-source`, it is so that on subsequent runs the tool will not waste time copying over source code again. So you should omit it after the first run.

# log
- TODO: handle retry on chat completion error (ratelimit, etc)

- Stretch: explore using alias analysis for better type recovery. We might not even need LLMs to restructure if we can just look for the `copy_from_user`s better.
