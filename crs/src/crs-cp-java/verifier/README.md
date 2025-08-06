# How to use
```
usage: verifier.py [-h] [--harness HARNESS] [--pov POV]

options:
  -h, --help         show this help message and exit
  --harness HARNESS  harness id
  --pov POV          pov data blob path
```

# Verifier
1. Check whether the given POV really triggers the bug.
2. Figure out which AIxCC sanitizer is triggered by the given POV.
3. Figure out which commit is the corresponding bug-inducing commit.
4. Submit POV and POU (AIxCC sanitizer and bug-inducing commit) through iAPI.
=> This will be handled by the verifier module. This verifier.py will just forward to it.
