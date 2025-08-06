FROM ubuntu:22.04

ARG SSH_PRIVATE_KEY

# Python dependency
COPY requirements.txt .

# Update package lists and install necessary packages
RUN apt-get update && \
    apt-get install -y git python3 python3-pip openssh-client \
    wget bison flex libelf-dev bc libssl-dev \
    qemu-system-x86

# Install Python dependencies using pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy ssh key
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    touch /root/.ssh/known_hosts && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts

# Clone cp-linux
RUN git clone git@github.com:Team-Atlanta/cp-linux.git

# Prepare linux 6.1.68
WORKDIR /cp-linux/samples/bin
RUN ./prepare.sh

# Download bookworm
WORKDIR /cp-linux/CVEs
RUN ./bin/download-rootfs.py bookworm

# Download/Install go 1.21.4
WORKDIR /root
RUN wget https://go.dev/dl/go1.21.4.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.4.linux-amd64.tar.gz

# Export PATH
ENV PATH="{$PATH}:/usr/local/go/bin"

# Install gcc cross compilers(Required by syzkaller)
RUN apt-get install -y gcc-arm-linux-gnueabi gcc-aarch64-linux-gnu gcc-mips64el-linux-gnuabi64 gcc-powerpc64le-linux-gnu gcc-riscv64-linux-gnu gcc-s390x-linux-gnu 
# Install clang-format(Required by syzkaller)
RUN apt-get install -y clang-format

# Run CMD
CMD ["/bin/bash"]
