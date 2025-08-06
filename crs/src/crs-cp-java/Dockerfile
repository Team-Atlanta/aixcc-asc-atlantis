# This is just a sample Dockerfile
# Competitors: You MUST implement your own Dockerfile here so that your container/s can be built
# and published to your CRS repo

FROM ubuntu:22.04

WORKDIR /app
ENV USER root
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=America/New_York \
    JAVA_WORK=/app/work/java \
    JAVA_CRS_HOME=/app/crs-cp-java/ \
    JAVA_CRS_SRC=/app/crs-cp-java/src \
    JAVA_FUZZER_SRC=/app/crs-cp-java/src/fuzzer
ARG DEBIAN_FRONTEND=noninteractive
ARG JAVA_CRS_BASE=.

RUN apt-get update && apt-get -y install curl jq \
        sudo \
        gosu \
        7zip \
        autoconf \
        automake \
        autotools-dev \
        bash \
        bsdextrautils \
        build-essential \
        binutils \
        ca-certificates \
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
        rsync \
        software-properties-common \
        strace \
        tar \
        tzdata \
        unzip \
        vim \
        wget \
        xz-utils \
        zip openssh-client redis-server \
        php default-jre \
        net-tools

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
    apt-get update; \
    apt-get install -y --no-install-recommends \
        containerd.io \
        docker-ce \
        docker-ce-cli \
        docker-buildx-plugin; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/* \
    gosu nobody true

RUN pip3 install --upgrade pip
#RUN apt-get autoremove -y
RUN apt-get clean && rm -rf /var/lib/{apt,dpkg,cache,log}

# Create working directory
RUN mkdir -p $JAVA_WORK && chmod -R 0755 $JAVA_WORK

# Create CRS directories
RUN mkdir -p $JAVA_CRS_HOME && chmod -R 0755 $JAVA_CRS_HOME
#ADD --chmod=0755 ${JAVA_CRS_BASE} ${JAVA_CRS_SRC}
WORKDIR $JAVA_WORK

# Copy your source code
#COPY ${JAVA_CRS_BASE}/crs-run.sh .

# Run the command to start your CRS, this is just a placeholder
# CMD ["./crs-run.sh"]
