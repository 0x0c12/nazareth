FROM python:3.12-slim


RUN apt-get update && apt-get install -y \
    gdb \
    tshark \
    strace \
    socat \
    && pip install --no-cache-dir pwntools
RUN useradd -m quiche
USER quiche

WORKDIR /home/quiche
