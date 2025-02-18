FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update -y && \
    apt-get install -y curl gnupg python3 python3-pip tmux && \
    pip3 install --break-system-packages pipenv

# Install ngrok
RUN curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list && \
    apt-get update -y && \
    apt-get install -y ngrok && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/eval_tool

