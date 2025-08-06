# CRS Userspace

### Run CRS

Set environment variables
```
export LITELLM_KEY=sk-...   
export LITELLM_URL=http://bombshell.gtisc.gatech.edu:4000
```


```bash
# make a clean workspace
rm -r ./crs_scratch
rm -r ./cp_root

# by default, it only loads the first folder in ./cp_root
# if you want to fuzz a specific CP, e.g., mock-cp
# please remove cp-nginx and any other CPs before using run-docker.sh
./run-docker.sh 

# for oss-fuzz eval
# rm cp_root and crs_scratch first
./run-docker.sh oss-25377
./run-docker.sh oss-25515
./run-docker.sh oss-25589
./run-docker.sh oss-32649

# for in-house cp-user eval
# rm cp_root and crs_scratch first
./run-docker.sh cp-user-itoa
./run-docker.sh cp-user-babynote
./run-docker.sh cp-user-libcue
# use a lot of LLM credit
./run-docker.sh cp-user-openssl


# special CPs eval
# 2 sources and 2 harnesses
./run-docker.sh cp-mock-multi-src

# has two sources(cromu-00002 and yan01-00012) and two harnesses
./run-docker.sh cp-cqe 

# has a single source(nrfin-00004) and two harnesses
./run-docker.sh cp-nrfin-00004 

# for arvo eval
# rm ./cp_root and ./crs_scratch first
./run-docker.sh arvo-11060
```
