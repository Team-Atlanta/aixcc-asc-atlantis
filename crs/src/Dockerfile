# This is just a sample Dockerfile
# Competitors: You MUST implement your own Dockerfile here so that your container/s can be built
# and published to your CRS repo

FROM ubuntu:22.04

WORKDIR /app

RUN apt-get update && apt-get -y install curl jq && apt-get clean && rm -rf /var/lib/{apt,dpkg,cache,log}
