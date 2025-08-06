FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y software-properties-common wget

# Install python3.11
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.11 python3.11-venv python3-pip

# Set python3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN python3 -m pip install --upgrade pip

# Install yq
ARG YQ_VERSION=4.43.1
ARG YQ_BINARY=yq_linux_amd64
RUN wget -q https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/${YQ_BINARY} -O /usr/bin/yq && \
    chmod +x /usr/bin/yq

# Dependency to build linux
# RUN apt update && \
#     apt install -y make gcc bc libelf-dev

# Dependency to build smith
RUN apt update && \
    apt install -y clang libclang-dev git universal-ctags

# Dependency to build loop
RUN apt update && \
    apt install -y pipx
RUN pipx install poetry
ENV PATH="${PATH}:/root/.local/bin"

# Install docker
RUN apt update
RUN apt install -y ca-certificates curl
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
RUN chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
   tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt update
RUN apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Build run.py
WORKDIR /home/crs-patch/
COPY ./requirements.txt /home/crs-patch/requirements.txt
RUN pip3 install -r ./requirements.txt

# Build smith
WORKDIR /home/crs-patch/smith
COPY ./smith/requirements.txt /home/crs-patch/smith/requirements.txt
RUN pip3 install -r ./requirements.txt

# Build swe-agent
RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make
RUN apt-get install -y rsync

# Set git config
# Need to pull source from git
RUN git config --global user.email "atlanta@team.com"
RUN git config --global user.name "Team Atlanta"

# Environment variables
ENV ROOT='/dev/'
RUN prompt() { echo " > "; };
ENV PS1="> "

# Create file for tracking edits, test patch
RUN touch /root/files_to_edit.txt
RUN touch /root/test.patch

# add ls file indicator
RUN echo "alias ls='ls -F'" >> /root/.bashrc

# Install miniconda
# ENV PATH="/root/miniconda3/bin:${PATH}"
WORKDIR /home/crs-patch/
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-1-Linux-x86_64.sh -O miniconda.sh
RUN mkdir /root/.conda \
    && bash miniconda.sh -b \
    && rm -f miniconda.sh

ARG PATH="/root/miniconda3/bin:${PATH}"
RUN conda --version \
    && conda init bash \
    && conda config --append channels conda-forge
    
# Build loop
WORKDIR /home/crs-patch/loop
COPY ./loop/pyproject.toml /home/crs-patch/loop/pyproject.toml
COPY ./loop/poetry.lock /home/crs-patch/loop/poetry.lock
COPY ./loop/dependencies/redia /home/crs-patch/loop/dependencies/redia
RUN poetry lock --no-update
RUN poetry install

# Copy entire source code later for caching
WORKDIR /home/crs-patch
COPY ./smith /home/crs-patch/smith
COPY ./loop /home/crs-patch/loop
COPY ./checker /home/crs-patch/checker
COPY ./runner /home/crs-patch/runner
COPY ./tracker /home/crs-patch/tracker
COPY ./utils /home/crs-patch/utils
COPY ./verifier /home/crs-patch/verifier
COPY ./watcher.py /home/crs-patch/watcher.py
COPY ./run.py /home/crs-patch/run.py

WORKDIR /home
CMD python3 -m crs-patch.run --cp-root $AIXCC_CP_ROOT --crs-scratch $AIXCC_CRS_SCRATCH_SPACE --validate
