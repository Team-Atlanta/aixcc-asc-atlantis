# This is just a sample Dockerfile
# Competitors: You MUST implement your own Dockerfile here so that your container/s can be built
# and published to your CRS repo

ARG IMAGE_NAME=ubuntu
ARG IMAGE_VERSION=sha256:aa772c98400ef833586d1d517d3e8de670f7e712bf581ce6053165081773259d
ARG PARENT_IMAGE=$IMAGE_NAME@$IMAGE_VERSION
# hadolint ignore=DL3006
FROM $PARENT_IMAGE as crs-base-image

# global environment variables
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=America/New_York \
    USER=root \
    WORK=/root/work \
    CRS_HOME=/root/crs \
    CRS_SRC=/root/crs/src \
    CRS_LIB=/root/crs/src/scripts \
    CRS_TEST=/root/crs/test

# install basic dependencies
# hadolint ignore=DL3008
RUN set -eux; \
    DEBIAN_FRONTEND=noninteractive apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        7zip \
        autoconf \
        automake \
        autotools-dev \
        bash \
        bsdextrautils \
        build-essential \
        binutils \
        ca-certificates \
        curl \
        file \
        gnupg2 \
        git \
        git-lfs \
        gzip \
        jq \
        libcap2 \
        ltrace \
        make \
        openssl \
        patch \
        perl-base \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-venv \
        rsync \
        software-properties-common \
        strace \
        sudo \
        tar \
        tree \
        tzdata \
        unzip \
        vim \
        wget \
        xz-utils \
        zip; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/*

#Dependency to build reverser
RUN apt update && \
    apt install -y ninja-build clang nlohmann-json3-dev cmake zlib1g-dev llvm

ARG YQ_VERSION=4.43.1
ARG YQ_BINARY=yq_linux_amd64
RUN wget -q https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/${YQ_BINARY} -O /usr/bin/yq && \
    chmod +x /usr/bin/yq

# Install Docker for CP repo build and test
# hadolint ignore=DL3008,DL4001,DL4006,SC1091
RUN set -eux; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc; \
    chmod a+r /etc/apt/keyrings/docker.asc; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    DEBIAN_FRONTEND=noninteractive apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        containerd.io \
        docker-ce \
        docker-ce-cli \
        docker-buildx-plugin; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/*

# Install Nix
ARG NIX_VERSION=nix-2.23.0
ARG NIX_INSTALLER=${NIX_VERSION}-x86_64-linux
ARG NIX_TAR=${NIX_INSTALLER}.tar.xz
RUN wget https://releases.nixos.org/nix/${NIX_VERSION}/${NIX_TAR}
RUN tar xf $NIX_TAR
WORKDIR $NIX_INSTALLER
RUN mkdir -p /etc/nix
RUN echo "build-users-group =" > /etc/nix/nix.conf
RUN ./install --yes --no-daemon --no-channel-add

# Create working directory
RUN mkdir -p $WORK && chmod -R 0755 $WORK
WORKDIR $WORK

# Create CRS directories
RUN mkdir -p $CRS_HOME && chmod -R 0755 $CRS_HOME

# ===== crs-cp-user start
WORKDIR $CRS_HOME
ENV CRS_USER=$CRS_HOME/crs-cp-user

# gcc for instrumentation
RUN apt-get update && apt-get install -y \ 
    gcc gcc-multilib cmake g++ git libz3-dev ninja-build zlib1g-dev pkg-config

# RUN apt-get update && apt-get install -y gcc 
RUN gcc_version=$(gcc -dumpversion | cut -d. -f1) && \
    apt-get install -y gcc-${gcc_version}-plugin-dev

# LLVM
RUN apt-get update && apt-get install -y \ 
    llvm-dev clang lld

# For commit analyzer
RUN apt install -y libclang-dev
RUN apt update && \
    apt install -y libmnl-dev libnftnl-dev
RUN apt install -y openssh-server isc-dhcp-client

WORKDIR $CRS_USER
COPY ./requirements-arvo.txt $CRS_USER/requirements-arvo.txt
RUN pip3 install -r requirements-arvo.txt

COPY ./requirements.txt $CRS_USER/requirements.txt
RUN pip3 install -r requirements.txt

COPY ./preprocessor/requirements.txt $CRS_USER/requirements-preprocessor.txt
RUN pip3 install -r requirements-preprocessor.txt


COPY ./reverser/requirements.txt $CRS_USER/requirements-reverser.txt
RUN python3 -m venv ./venv-reverser
RUN ./venv-reverser/bin/pip3 install -r requirements-reverser.txt
WORKDIR $CRS_USER/reverser/static
COPY ./reverser/static $CRS_USER/reverser/static
RUN ./build.sh

WORKDIR $CRS_USER
COPY ./verifier/requirements.txt $CRS_USER/requirements-verifier.txt
RUN python3 -m venv ./venv-verifier
RUN ./venv-verifier/bin/pip3 install -r requirements-verifier.txt

COPY ./commit-analyzer/requirement.txt $CRS_USER/requirements-commit-analyzer.txt
RUN python3 -m venv ./venv-commit-analyzer
RUN ./venv-commit-analyzer/bin/pip3 install -r requirements-commit-analyzer.txt

COPY ./llm-seed-generator-c/requirements.txt $CRS_USER/requirements-llm-seed-generator-c.txt
RUN python3 -m venv ./venv-llm-seed-generator-c
RUN ./venv-llm-seed-generator-c/bin/pip3 install -r requirements-llm-seed-generator-c.txt

WORKDIR $CRS_USER
COPY ./crs-agi/requirements.txt $CRS_USER/requirements-crs-agi.txt
RUN python3 -m venv ./venv-crs-agi
RUN ./venv-crs-agi/bin/pip3 install -r requirements-crs-agi.txt

# set up cargo dependencies
RUN curl https://sh.rustup.rs -sSf | \
    sh -s -- --default-toolchain nightly -y
ENV PATH=/root/.cargo/bin:$PATH

RUN rustup toolchain install nightly-2024-06-18
RUN rustup default nightly-2024-06-18
RUN rustup target add i686-unknown-linux-gnu

# NOTE Andrew: disabling, unless Daeryong's build process changes
# WORKDIR $CRS_USER/assets
# RUN tar xJf ./clang-17.tar.xz

FROM crs-base-image AS crs-cp-user

WORKDIR $CRS_USER
COPY ./nix ./nix
COPY ./preprocessor ./preprocessor
COPY ./reverser ./reverser
COPY ./commit-analyzer ./commit-analyzer
COPY ./verifier ./verifier
COPY ./crs-agi ./crs-agi
COPY ./llm-seed-generator-c ./llm-seed-generator-c

# Move venvs into respective subdir, now that they are created
RUN mv ./venv-reverser ./reverser/.venv
RUN mv ./venv-verifier ./verifier/.venv
RUN mv ./venv-commit-analyzer ./commit-analyzer/.venv
RUN mv ./venv-crs-agi ./crs-agi/.venv
RUN mv ./venv-llm-seed-generator-c ./llm-seed-generator-c/.venv

# third parties
WORKDIR $CRS_USER
COPY ./third_party ./third_party

# libafl_libfuzzer
WORKDIR $CRS_USER
COPY ./libafl_libfuzzer ./libafl_libfuzzer
COPY ./libafl_libfuzzer ./libafl_libfuzzer_nix

WORKDIR $CRS_USER/nix
RUN . $HOME/.nix-profile/etc/profile.d/nix.sh && nix --extra-experimental-features nix-command --extra-experimental-features flakes develop -c ./cd_and_build.sh $CRS_USER/libafl_libfuzzer_nix
RUN . $HOME/.nix-profile/etc/profile.d/nix.sh && nix --extra-experimental-features nix-command --extra-experimental-features flakes develop -c ./get-all-runtimes.sh > nix_runtimes.txt

WORKDIR $CRS_USER/libafl_libfuzzer

# dynamic linking
RUN cargo build --release
# static linking
ENV RUSTFLAGS="-C target-feature=+crt-static"
RUN cargo build --release --target x86_64-unknown-linux-gnu
RUN cargo build --release --target i686-unknown-linux-gnu

# TODO uncomment if I refactor run.py's cp -r .rustup in time
# # cargo vendor
# RUN cargo vendor
# RUN mkdir -p .cargo
# RUN echo -e '[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "vendor"\n' > .cargo/config.toml

# hybrid fuzzer
WORKDIR $CRS_USER
# # env vars for building libafl_hybrid
# ENV LLVM_DIR=$CRS_USER/assets/clang+llvm-17.0.6-x86_64-linux-gnu-ubuntu-22.04/lib/cmake/llvm
# # LibAFL Hybrid
# WORKDIR $CRS_USER
# COPY ./libafl_hybrid ./libafl_hybrid
# WORKDIR $CRS_USER/libafl_hybrid/runtime
# RUN cargo build --release
# WORKDIR $CRS_USER/libafl_hybrid/fuzzer
# RUN cargo build --release
# # unset LLVM_DIR
# ENV LLVM_DIR=

# assets
WORKDIR $CRS_USER
COPY ./project_analyzer ./project_analyzer
# COPY ./fuzz_corpus ./fuzz_corpus
COPY ./fuzz_corpus1.zip ./fuzz_corpus1.zip
COPY ./fuzz_corpus2.zip ./fuzz_corpus2.zip
RUN unzip fuzz_corpus1.zip
RUN unzip fuzz_corpus2.zip
COPY ./oss-fuzz-dict ./oss-fuzz-dict

# other utils
WORKDIR $CRS_USER
COPY ./run_pov.sh ./run_pov.sh
COPY ./cp_config.yaml ./cp_config.yaml
COPY ./Makefile ./Makefile
COPY ./harness_repo_matcher.py ./harness_repo_matcher.py
COPY ./run.py ./run.py

# reset the workdir
WORKDIR $CRS_USER
