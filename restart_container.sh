docker stop scholawrite_container
docker rm scholawrite_container

docker run --name scholawrite_container --gpus all -dt -v ./:/workspace --ipc=host pytorch/pytorch:2.2.1-cuda11.8-cudnn8-runtime bash

#docker exec -it scholawrite_container bash

docker exec -it scholawrite_container pip install -r requirements.txt

#docker exec -it scholawrite_container python /workspace/src/intention_classifier.py

#docker exec -it scholawrite_container ls
