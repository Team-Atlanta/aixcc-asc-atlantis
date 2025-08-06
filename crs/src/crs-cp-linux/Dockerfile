FROM ubuntu:22.04 as crs-cp-linux-base

ENV DEBIAN_FRONTEND=noninteractive
#Dependency to build linux
RUN apt update && \
    apt install -y \
        make gcc bc libelf-dev \
        python3 python3-pip ninja-build meson pkg-config libglib2.0-dev libpixman-1-dev \
        ninja-build clang nlohmann-json3-dev cmake zlib1g-dev llvm \
        busybox-static python3 libvirt-daemon-system wget bc binutils bison \
        build-essential dwarves flex gcc git gnupg2 gzip libelf-dev libncurses5-dev libssl-dev make openssl \
        pahole perl-base rsync tar xz-utils kmod file ca-certificates \
        clang-format libclang-dev libmnl-dev libnftnl-dev openssh-server isc-dhcp-client \
        liburing-dev unzip python3.10-venv curl && \
    rm -rf /var/lib/apt/lists/*

# Install docker
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# For builidng CPs
RUN wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq &&\
    chmod +x /usr/bin/yq

# Download/Install go 1.21.4
WORKDIR /
RUN wget https://go.dev/dl/go1.21.4.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.4.linux-amd64.tar.gz && \
    rm go1.21.4.linux-amd64.tar.gz

# Export PATH
ENV PATH="{$PATH}:/usr/local/go/bin"

# Directories used by go
RUN mkdir /go /.cache && chmod 777 /go /.cache

# Install virtme-ng
RUN pip3 install virtme virtme-ng

FROM crs-cp-linux-base as crs-cp-linux-seeds

# Build seed-selector
WORKDIR /home/crs-cp-linux/fuzzer/seed-selector
COPY ./fuzzer/seed-selector/ /home/crs-cp-linux/fuzzer/seed-selector/
RUN pip3 install -r ./requirements.txt
RUN unzip ./assets/corpus.zip -d ./assets 
RUN mkdir ./assets/bin/
COPY ./fuzzer/SkyTracer /home/crs-cp-linux/fuzzer/SkyTracer
RUN /home/crs-cp-linux/fuzzer/SkyTracer/prepare_target.py --dir ./assets/code/
RUN ./compile.py --src-dir ./assets/code/ --out-dir ./assets/bin/

FROM crs-cp-linux-seeds as crs-cp-linux-pip
# Build run.py
WORKDIR /home/crs-cp-linux/
COPY ./requirements.txt /home/crs-cp-linux/requirements.txt
RUN pip3 install -r ./requirements.txt

# Build reverser
WORKDIR /home/crs-cp-linux/fuzzer/reverser
COPY ./fuzzer/reverser/requirements.txt /home/crs-cp-linux/fuzzer/reverser/requirements.txt
RUN pip3 install -r ./requirements.txt
WORKDIR /home/crs-cp-linux/fuzzer/reverser/static
COPY ./fuzzer/reverser/static /home/crs-cp-linux/fuzzer/reverser/static
RUN ./build.sh

# Build converter
WORKDIR /home/crs-cp-linux/fuzzer/converter
COPY ./fuzzer/converter/requirements.txt /home/crs-cp-linux/fuzzer/converter/requirements.txt
RUN pip3 install -r ./requirements.txt

# Build commit-analyzer
COPY ./commit-analyzer/requirement.txt /home/crs-cp-linux/commit-analyzer/requirement.txt
WORKDIR /home/crs-cp-linux/commit-analyzer
RUN pip3 install -r ./requirement.txt

# Build CVE-analyzer
WORKDIR /home/crs-cp-linux/CVE-analyzer/
COPY ./CVE-analyzer/ /home/crs-cp-linux/CVE-analyzer/
RUN pip3 install -r ./requirements.txt
RUN mkdir -p /data/db

# Build Verifier
WORKDIR /home/crs-cp-linux/verifier/vapi-client 
COPY ./verifier/vapi-client/requirements.txt /home/crs-cp-linux/verifier/vapi-client/requirements.txt
RUN pip3 install -r ./requirements.txt

# Build SkyTracer
WORKDIR /home/crs-cp-linux/fuzzer/SkyTracer
RUN pip3 install -r ./requirements.txt
RUN make -j$(nproc)

FROM crs-cp-linux-pip as crs-cp-linux-final

# Build POCs in CVE-analyzer
WORKDIR /home/crs-cp-linux/CVE-analyzer/POCs
COPY ./CVE-analyzer/POCs /home/crs-cp-linux/CVE-analyzer/POCs
RUN /home/crs-cp-linux/fuzzer/SkyTracer/prepare_target.py --poc-dir /home/crs-cp-linux/CVE-analyzer/POCs
RUN ./build.sh

# Build Syzlang-gen
WORKDIR /home/crs-cp-linux/fuzzer/syzlang-gen/SyzDescribe
COPY ./fuzzer/syzlang-gen/SyzDescribe/ /home/crs-cp-linux/fuzzer/syzlang-gen/SyzDescribe/
RUN ./setup.sh
RUN pip3 install -r ./requirements.txt

# Build syz-reverser, syzkaller
COPY ./fuzzer/syzkaller /home/crs-cp-linux/fuzzer/syzkaller
WORKDIR /home/crs-cp-linux/fuzzer/syzkaller
RUN git init
RUN git add README.md
RUN git config --global user.email "atlanta@team.com"
RUN git config --global user.name "Team Atlanta"
RUN git commit -m "Dummy commit"
RUN make reverser
RUN make generate
RUN make
RUN cp -r /home/crs-cp-linux/fuzzer/syzkaller /home/crs-cp-linux/fuzzer/syz-reverser

# Build SkyQEMU
COPY ./fuzzer/SkyQEMU/libsym /home/crs-cp-linux/fuzzer/SkyQEMU/libsym
COPY ./fuzzer/SkyQEMU/qemu /home/crs-cp-linux/fuzzer/SkyQEMU/qemu
COPY ./fuzzer/SkyQEMU/Makefile /home/crs-cp-linux/fuzzer/SkyQEMU/Makefile
WORKDIR /home/crs-cp-linux/fuzzer/SkyQEMU
RUN make
COPY ./fuzzer/SkyQEMU/requirements.txt /home/crs-cp-linux/fuzzer/SkyQEMU/requirements.txt
RUN pip3 install -r ./requirements.txt

# Copy entire source code later for caching
WORKDIR /home/crs-cp-linux
COPY ./fuzzer /home/crs-cp-linux/fuzzer
COPY ./verifier /home/crs-cp-linux/verifier
COPY ./commit-analyzer /home/crs-cp-linux/commit-analyzer
COPY ./run.py /home/crs-cp-linux/run.py

COPY ./llm-result /home/crs-cp-linux/llm-result
COPY ./crs-linux.config* /
CMD ./run.py --cp-root $AIXCC_CP_ROOT --build-dir $AIXCC_CRS_SCRATCH_SPACE
