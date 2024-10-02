docker run --name scholawrite_container --gpus all -dt -v ./:/workspace --ipc=host pytorch/pytorch:2.2.1-cuda11.8-cudnn8-runtime bash

docker exec -it scholawrite_container bash
