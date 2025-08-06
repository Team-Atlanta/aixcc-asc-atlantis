# Reverser
```
This reverser will automatically infer the input format of test harness provided by AIxCC Organizer.
```
- The AIxCC provided test harness example is [here](https://github.com/Team-Atlanta/cp-linux-exemplar-source/blob/main/test_harnesses/linux_test_harness.c)
```
INPUT ::= COMMAND_CNT { size: 4 }
          COMMAND[COMMAND_CNT]

COMMAND ::= SEND_PACKET
          | SEND_NETLINK_PACKET

SEND_PACKET ::= OPCODE { size: 4, value: 0 }
                SIZE { size: 4 }
                FLAGS { size: 4 }
                PACKET_DATA { size: SIZE }

SEND_NETLINK_PACKET ::= OPCODE { size: 4, value: 1 }
                        MSG_TYPE { size: 4 }
                        MSG_FLAGS { size: 4 }
                        NETLINK_PROTOCOL { size: 4 }
                        SIZE { size: 4 }
                        DATA { size: SIZE }
```

# How to setup
```
pip3 install -r ./requirements.txt
```
- Put LITELLM_URL and LITELLM_KEY in .env like this

```
LITELLM_URL=http://bombshell.gtisc.gatech.edu:4000
LITELLM_KEY=sk-KEY
```

# Handwritten testlangs
Available in `answers/`.

These grammars were manually created and match the input formats for the test
harnesses created by the benchmark team. We use them to verify and test our
testlang generation tool.

**Use these for testing other modules to avoid unnecessary usage of LLM credits.**

# Running main reverser command
```
usage: run.py [-h] --workdir WORKDIR --target TARGET --output OUTPUT
              [--model {claude-3-haiku,claude-3-sonnet,gpt-3.5-turbo,gpt-4-turbo,claude-3-opus}] [-v]

Infer the input format of test harness

options:
  -h, --help            show this help message and exit
  --workdir WORKDIR     Working directory
  --target TARGET       Path to target test harness
  --output OUTPUT       Path to output testlang
  --model {claude-3-haiku,claude-3-sonnet,gpt-3.5-turbo,gpt-4-turbo,claude-3-opus}
                        LLM model to use
  -v, --verbose         Verbose information printed
```

Example usage:
```
./run.py --workdir /workdir \
         --target /cp-linux-exemplar-source/test_harnesses/linux_test_harness.c \
         --output /workdir/linux_test_harness.testlang
```

# Testing in Docker
- Script copies local files from `<CRS-cp-linux>/fuzzer/reverser`. If you have a
  dirty development directory, then it is best to clone a fresh `CRS-cp-linux` for testing
- Add the following config to `<CRS-cp-linux>/crs-linux.config`
```json
{
  "target_harness": ["CVE-2022-0995"],
  "modules": ["Reverser"],
  "build_cache":true,
  "debug": true
}
```
- Set `LITELLM_URL` and `LITELLM_KEY` as shell environment variables
- Execute `<CRS-cp-linux>/run-docker.sh`. You can see the generated testlang on `/crs-workdir/<benchmark>/testlang`.
