FROM nvidia/cuda:12.2.0-base-ubuntu20.04
WORKDIR /workspace

RUN apt-get update && \
    apt-get install -y python3.9 && \
    apt-get install -y python3-pip

RUN pip3 install --upgrade pip

#COPY requirements.txt .
#RUN pip install --no-cache-dir -r ./requirements.txt && rm requirements.txt

RUN pip3 install torch torchvision torchaudio


