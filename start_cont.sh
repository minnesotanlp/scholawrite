docker run --name schola_2 --gpus all -dt -v ./:/workspace --ipc=host pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel bash
docker exec -it schola_2 bash