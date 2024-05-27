# Docker Set Up

Note: you can replace `scholawrite_fine_tuning` with a different conatiner name if you want to run seperately

BUILD: `docker build -t scholawrite_fine_tuning . -f Dockerfile`

START: `docker run --name scholawrite_fine_tuning --gpus 0 -dt -v $(pwd):/workspace --ipc=host --net=host pytorch/pytorch:2.2.1-cuda11.8-cudnn8-runtime bash`

RUN: `docker exec -it scholawrite_fine_tuning bash`

## Environment

in docker, run `pip install -r requirements.txt` to install necessary requirements

NOTE: you might need to manually install some packages too if this is not up to date with all the files.

# Training

run: `python llama3_qlora_diff.py`

# Inference

run: `python diff_inference.py`