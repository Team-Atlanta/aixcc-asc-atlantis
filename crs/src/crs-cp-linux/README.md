# CRS-cp-linux
0. `git lfs pull`

1. set up `crs-linux.config`
Default:
```
{}
```

Options:
```
{
  "target_harness": ["CVE-2022-0995"],
  "modules": [ "Syz-Reverser", "Syzkaller"], 
  "build_cache":true,
  "debug": true
}
```
This will run only CVE-analyzer.

Here is a list of available modules.
- Reverser (very expensive)
- CVE-analyzer
- Converter
- Syz-Reverser
- Syzkaller

2. run docker
```
./run-docker.sh
```
