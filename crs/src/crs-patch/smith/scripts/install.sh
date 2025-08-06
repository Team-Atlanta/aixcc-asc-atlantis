#!/bin/bash

# Install dependencies
sudo apt-get update

# Clangd-17
echo " [+] Installing clangd-17..."
sudo apt-get install -y clangd-17
sudo update-alternatives --install /usr/bin/clangd clangd /usr/bin/clangd-17 100
/usr/bin/clangd --version | grep "clangd version 17" || exit 1

# Java 17
echo " [+] Installing OpenJDK 17..."
sudo apt install -y openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
export PATH=$JAVA_HOME/bin:$PATH
java --version | grep "openjdk 17" || exit 1

# Eclipse.jdt.ls
echo " [+] Installing Eclipse.jdt.ls..."
mkdir -p opt/eclipse.jdt.ls && \
    curl -L "https://www.eclipse.org/downloads/download.php?file=/jdtls/milestones/1.34.0/jdt-language-server-1.34.0-202404031240.tar.gz" | \
    tar -xz -C opt/eclipse.jdt.ls

echo " [+] Installation complete!"

# mock-cp (Userland C challenge)
sudo snap install yq

