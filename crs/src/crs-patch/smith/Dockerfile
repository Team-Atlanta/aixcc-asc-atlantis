FROM bqcuongas/vul4j

RUN dpkg --add-architecture i386
RUN apt update && apt upgrade -y
RUN apt install -y libc6-i386 python3-pip
RUN pip install bs4 coloredlogs defusedxml libclang lxml numpy openai pandas pwntools requests tiktoken toml transformers

RUN apt install -y gcc-multilib g++-multilib libc6-dev-i386
RUN apt install -y poppler-utils texlive-latex-base