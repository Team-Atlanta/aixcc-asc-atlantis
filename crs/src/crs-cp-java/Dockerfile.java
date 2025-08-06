# Stage 0-0 - Build naive Jazzer

FROM gcr.io/oss-fuzz-base/base-builder@sha256:770700ccc95934ec0ad92686036baebbbbdb472fa6bf9b5ea9263b9540a03b12 \
    as jazzer_base_naive

ENV JAZZER_API_PATH "/usr/local/lib/jazzer_api_deploy.jar"

# RUN apt-get clean && apt-get update && apt-get install -y maven

COPY fuzzer/jazzer /src/jazzer
WORKDIR $SRC/jazzer
RUN bazel build //:jazzer_release &&  \
    mkdir /classpath && mkdir /classpath/jazzer && \
    cp bazel-bin/jazzer_release.tar.gz /classpath/jazzer && \
    cp bazel-out/k8-opt/bin/src/main/java/com/code_intelligence/jazzer/utils/libunsafe_provider.jar /classpath/jazzer && \
    cp bazel-bin/src/main/java/com/code_intelligence/jazzer/jazzer_standalone_deploy.jar /classpath/jazzer && \
    cp bazel-out/k8-opt/bin/deploy/jazzer-api-project.jar /classpath/jazzer && \
    cd /classpath/jazzer && tar -xzvf jazzer_release.tar.gz && rm jazzer_standalone.jar && rm jazzer_release.tar.gz

# Stage 0-1 - Build directed Jazzer

FROM gcr.io/oss-fuzz-base/base-builder@sha256:770700ccc95934ec0ad92686036baebbbbdb472fa6bf9b5ea9263b9540a03b12 \
    as jazzer_base_directed

ENV JAZZER_API_PATH "/usr/local/lib/jazzer_api_deploy.jar"

RUN apt-get clean && apt-get update && apt-get install -y maven

COPY fuzzer/jazzer-directed /src/jazzer_directed
WORKDIR $SRC/jazzer_directed
RUN bazel build //:jazzer_release &&  \
    mkdir /classpath && mkdir /classpath/jazzer_directed && \
    cp bazel-bin/jazzer_release.tar.gz /classpath/jazzer_directed && \
    cp bazel-out/k8-opt/bin/src/main/java/com/code_intelligence/jazzer/utils/libunsafe_provider.jar /classpath/jazzer_directed && \
    cp bazel-bin/src/main/java/com/code_intelligence/jazzer/jazzer_standalone_deploy.jar /classpath/jazzer_directed && \
    cp bazel-out/k8-opt/bin/deploy/jazzer-api-project.jar /classpath/jazzer_directed && \
    cp third_party/SootUp/*/target/*.jar /classpath/jazzer_directed && \
    cd /classpath/jazzer_directed && tar -xzvf jazzer_release.tar.gz && rm jazzer_standalone.jar && rm jazzer_release.tar.gz

ADD fuzzer/sootup-dependencies.jar /classpath/jazzer_directed

# handle after cen's fix
# Stage 0-2 - Build ASC Jazzer

FROM gcr.io/oss-fuzz-base/base-builder@sha256:770700ccc95934ec0ad92686036baebbbbdb472fa6bf9b5ea9263b9540a03b12 \
    as jazzer_base_asc
ENV JAZZER_API_PATH "/usr/local/lib/jazzer_api_deploy.jar"

COPY fuzzer/jazzer-asc /src/jazzer_asc
WORKDIR $SRC/jazzer_asc
RUN bazel build //:jazzer_release &&  \
    mkdir /classpath && mkdir /classpath/jazzer_asc && \
    cp bazel-bin/jazzer_release.tar.gz /classpath/jazzer_asc && \
    cp bazel-out/k8-opt/bin/src/main/java/com/code_intelligence/jazzer/utils/libunsafe_provider.jar /classpath/jazzer_asc && \
    cp bazel-bin/src/main/java/com/code_intelligence/jazzer/jazzer_standalone_deploy.jar /classpath/jazzer_asc && \
    cp bazel-out/k8-opt/bin/deploy/jazzer-api-project.jar /classpath/jazzer_asc && \
    cd /classpath/jazzer_asc && tar -xzvf jazzer_release.tar.gz && rm jazzer_standalone.jar && rm jazzer_release.tar.gz


# Stage 1 - Env setup

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

RUN chmod 1777 /tmp

RUN apt-get clean && apt-get update && apt-get -y install curl jq \
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
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip
RUN apt-get clean && rm -rf /var/lib/{apt,dpkg,cache,log}

# Create working directory
RUN mkdir -p $JAVA_WORK && chmod -R 0755 $JAVA_WORK

# Create CRS directories
RUN mkdir -p $JAVA_CRS_HOME && chmod -R 0755 $JAVA_CRS_HOME
WORKDIR $JAVA_WORK


################################################################################
# Here start our own additions
################################################################################

ARG DEV
ARG JAVA_CRS_BASE=.

ENV JOERN_DIR /joern
ENV JOERN_CLI $JOERN_DIR/joern-cli
ENV JAVA2CPG $JOERN_DIR/joern-cli/frontends/javasrc2cpg/bin

# Install Java
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64
ENV JVM_LD_LIBRARY_PATH $JAVA_HOME/lib/server
ENV PATH $PATH:$JAVA_HOME/bin:$JOERN_CLI:$JAVA2CPG

# add java
WORKDIR /tmp/
RUN echo "Installing Modified JAVA"
RUN if ! test -f /openlogic-openjdk-17.0.11+9-linux-x64.tar.gz; then echo "from the internet...";curl -L -O https://builds.openlogic.com/downloadJDK/openlogic-openjdk/17.0.11+9/openlogic-openjdk-17.0.11+9-linux-x64.tar.gz;else echo "from cache";cp /openlogic-openjdk-17.0.11+9-linux-x64.tar.gz .;fi
RUN mkdir -p $JAVA_HOME
RUN tar -xz --strip-components=1 -f openlogic-openjdk-17.0.11+9-linux-x64.tar.gz --directory $JAVA_HOME
RUN rm -f openlogic-openjdk-17.0.11+9-linux-x64.tar.gz
RUN rm -rf $JAVA_HOME/lib/src.zip
WORKDIR $JAVA_WORK

# add mvn
WORKDIR /
RUN echo "Installing maven"
RUN curl -L -O https://dlcdn.apache.org/maven/maven-3/3.9.7/binaries/apache-maven-3.9.7-bin.tar.gz &&\
tar xzvf apache-maven-3.9.7-bin.tar.gz &&\
rm -f apache-maven-3.9.7-bin.tar.gz
ENV PATH $PATH:/apache-maven-3.9.7/bin
WORKDIR $JAVA_WORK

# add protobuf
WORKDIR /
RUN echo "Installing protobuf"
RUN mkdir protobuf &&\
cd protobuf &&\
curl -L -O https://github.com/protocolbuffers/protobuf/releases/download/v3.20.3/protoc-3.20.3-linux-x86_64.zip &&\
unzip protoc-3.20.3-linux-x86_64.zip &&\
rm -f protoc-3.20.3-linux-x86_64.zip &&\
mkdir jar &&\
curl -L -O https://repo1.maven.org/maven2/com/google/protobuf/protobuf-java/3.25.3/protobuf-java-3.25.3.jar &&\
mv protobuf-java-3.25.3.jar jar/ &&\
cd -
ENV PATH $PATH:/protobuf/bin
WORKDIR $JAVA_WORK

COPY --from=jazzer_base_naive /classpath/jazzer /classpath/jazzer
COPY --from=jazzer_base_directed /classpath/jazzer_directed /classpath/jazzer_directed
COPY --from=jazzer_base_asc /classpath/jazzer_asc /classpath/jazzer_asc

# add gradle
RUN echo "installing gradle"
RUN mkdir /opt/gradle
WORKDIR /opt/gradle
RUN curl -L -O https://services.gradle.org/distributions/gradle-8.8-bin.zip && \
    unzip gradle-8.8-bin.zip && \
    rm -f gradle-8.8-bin.zip
ENV PATH $PATH:/opt/gradle/gradle-8.8/bin
WORKDIR $JAVA_WORK

# add sbt
ENV SBT_VERSION 1.8.0
ENV SBT_HOME /usr/local/sbt
ENV PATH ${PATH}:${SBT_HOME}/bin
RUN echo "installing sbt"
RUN curl -sL "https://github.com/sbt/sbt/releases/download/v$SBT_VERSION/sbt-$SBT_VERSION.tgz" | gunzip | tar -x -C /usr/local

######### TODO: Remove this before release #####################################
ENV GITHUB_TOKEN=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
COPY ${JAVA_CRS_BASE}/assets/gitconfig /root/.gitconfig
COPY ${JAVA_CRS_BASE}/assets/known_hosts /root/.ssh/known_hosts
RUN chown 700 /root/.ssh
RUN chown 644 /root/.ssh/known_hosts
################################################################################

# Install dependencies for run.py
COPY $JAVA_CRS_BASE/requirements.txt $JAVA_WORK/requirements.txt
RUN pip3 install -r $JAVA_WORK/requirements.txt

# Install dependencies for java_dict_generator
RUN pip3 install virtualenv
ADD $JAVA_CRS_BASE/fuzzer/java_dict_generator $JAVA_WORK/java_dict_generator
RUN cd $JAVA_WORK/java_dict_generator &&\
bash build.sh &&\
cd -

# Install dependencies for java_introspected_fuzzing
ADD $JAVA_CRS_BASE/fuzzer/java_introspected_fuzzing $JAVA_WORK/java_introspected_fuzzing

# Install dependencies for java_harness_processor
ADD $JAVA_CRS_BASE/fuzzer/java_harness_processor $JAVA_WORK/java_harness_processor
RUN pip3 install -r $JAVA_WORK/java_harness_processor/requirements.txt

# Install dependencies for SWAT
# Build SWAT
ADD $JAVA_CRS_BASE/fuzzer/SWAT $JAVA_WORK/SWAT
WORKDIR $JAVA_WORK/SWAT
RUN sh -c "PATH=$PATH ./build.sh"
RUN pip3 install -r requirements.txt

# Install dependencies for llm_poc_gen
RUN mkdir $JAVA_WORK/llm_poc_gen
COPY $JAVA_CRS_BASE/llm_poc_gen/requirements.txt $JAVA_WORK/llm_poc_gen/requirements.txt
RUN pip3 install -r $JAVA_WORK/llm_poc_gen/requirements.txt

# Install dependencies for verifier / vapi-client
RUN mkdir -p $JAVA_WORK/verifier/vapi-client
COPY $JAVA_CRS_BASE/verifier/vapi-client/requirements.txt $JAVA_WORK/verifier/vapi-client/requirements.txt
RUN pip3 install -r $JAVA_WORK/verifier/vapi-client/requirements.txt

# Installing joern
RUN mkdir ${JOERN_DIR}
COPY ${JAVA_CRS_BASE}/joern/Joern/target/joern-cli.zip ${JOERN_DIR}/.
WORKDIR ${JOERN_DIR}
RUN unzip joern-cli.zip
ADD ${JAVA_CRS_BASE}/joern/Joern/autoScript ${JOERN_CLI}/autoScript
RUN chmod 777 ${JOERN_CLI}/autoScript
COPY ${JAVA_CRS_BASE}/joern/run-joern.py ${JOERN_CLI}/.
COPY ${JAVA_CRS_BASE}/joern/run-joern.sh ${JOERN_CLI}/.
COPY ${JAVA_CRS_BASE}/joern/requirements.txt ${JOERN_CLI}/.
RUN pip install -r ${JOERN_CLI}/requirements.txt

# Install dependencies for commit-analyzer
RUN mkdir -p $JAVA_WORK/commit-analyzer
COPY $JAVA_CRS_BASE/commit-analyzer/requirement.txt $JAVA_WORK/commit-analyzer/requirement.txt
RUN pip3 install -r $JAVA_WORK/commit-analyzer/requirement.txt

# Copy entire source code later for caching
WORKDIR $JAVA_WORK
COPY ${JAVA_CRS_BASE}/run.py .
COPY ${JAVA_CRS_BASE}/fuzzer/*.sh .
COPY ${JAVA_CRS_BASE}/joern/jazzer_adapter.sh .
COPY ${JAVA_CRS_BASE}/crs-*.config /

WORKDIR /app

ADD --chmod=0755 ${JAVA_CRS_BASE} $JAVA_CRS_SRC

WORKDIR $JAVA_WORK

COPY --chmod=0755 ${JAVA_CRS_BASE}/run.sh .
CMD ${JAVA_CRS_SRC}/run.py --cp-root ${AIXCC_CP_ROOT} --cmd run
