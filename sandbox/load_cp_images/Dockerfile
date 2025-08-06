FROM docker:26-cli

# hadolint ignore=DL3018
RUN apk add --no-cache make yq git git-lfs bash && \
    rm -rf /var/cache/apk/* && \
    ln -s "$(which bash)" /usr/bin/bash && \
    git lfs install

COPY gitconfig /root/.gitconfig
COPY run.sh /

ENTRYPOINT ["/run.sh"]
