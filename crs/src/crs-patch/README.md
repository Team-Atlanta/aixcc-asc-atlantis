# CRS-patch

0-1. Update submodules (smith & loop)
```bash
git submodule update --init
```

0-2. Update sub-submodules

Not to update all sub-submodules such as exemplars, update only necessary sub-submodules.
```bash
git -C smith submodule update --init ./smith/lib/aider
git -C smith submodule update --init ./smith/lib/swe_agent
git -C loop submodule update --init ./dependencies/redia
```

1. Run docker
```bash
./run-docker.sh
```