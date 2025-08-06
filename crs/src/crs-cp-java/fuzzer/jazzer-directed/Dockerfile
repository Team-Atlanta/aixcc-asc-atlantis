FROM gcr.io/oss-fuzz-base/base-builder@sha256:770700ccc95934ec0ad92686036baebbbbdb472fa6bf9b5ea9263b9540a03b12 \
    as fuzzer_base
ENV JAZZER_API_PATH "/usr/local/lib/jazzer_api_deploy.jar"

# Install maven
RUN apt-get update && apt-get install -y maven

COPY . /src/jazzer
WORKDIR $SRC/jazzer
RUN bazel build //:jazzer_release &&  \
    mkdir /classpath && mkdir /classpath/jazzer && \
    cp bazel-bin/jazzer_release.tar.gz /classpath/jazzer && \
    cp bazel-out/k8-opt/bin/src/main/java/com/code_intelligence/jazzer/utils/libunsafe_provider.jar /classpath/jazzer && \
    cp bazel-bin/src/main/java/com/code_intelligence/jazzer/jazzer_standalone_deploy.jar /classpath/jazzer && \
    cp bazel-out/k8-opt/bin/deploy/jazzer-api-project.jar /classpath/jazzer && \
    cd /classpath/jazzer && tar -xzvf jazzer_release.tar.gz && rm jazzer_standalone.jar && rm jazzer_release.tar.gz

FROM maven:3.9.6-eclipse-temurin-17

RUN mkdir /classpath

# the following commands require the bazel server to be running, and if they are separated out the server has to come up each time a new command is RUN (~4.5s each)
RUN <<EOR1
cp $(bazel cquery --output=files //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar) /classpath/jazzer/
cp $(bazel cquery --output=files //launcher:jazzer) /classpath/jazzer/
cp $(bazel cquery --output=files //deploy:jazzer-api) /classpath/jazzer/
cp $(bazel cquery --output=files //src/main/java/com/code_intelligence/jazzer/utils:unsafe_provider) /classpath/jazzer/
rm -rf ~/.cache/bazel ~/.cache/bazelisk
EOR1
