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
        rsync \
        software-properties-common \
        strace \
        tar \
        tzdata \
        unzip \
        vim \
        wget \
        xz-utils \
        zip; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/*

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

# Create working directory
RUN mkdir -p $WORK && chmod -R 0755 $WORK

# Create CRS directories
RUN mkdir -p $CRS_HOME && chmod -R 0755 $CRS_HOME

WORKDIR $CRS_HOME
COPY --chmod=0755 ./mock_crs/ .

WORKDIR $WORK
