# Static Analyzer Reverser
Fallback tool for reversing test harness in case LLM fails.
## Environment
Ubuntu 22.04 LTS, with default clang version in repos. Following packages were installed:
- clang
- llvm
## Build
```
cd <ROOT>
mkdir build
cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_INSTALL_PREFIX=./install -DCMAKE_BUILD_TYPE=Debug -B build -S . -G Ninja
cd build && ninja install
```
## Run pass
```
cd <ROOT>/install
./run_pass.sh <HARNESS>
```
