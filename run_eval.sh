docker run --name scholawrite_eval --gpus all -dt -v ./:/workspace --ipc=host --net=host ubuntu:latest bash

apt-get update -y && \
    apt-get install -y curl gnupg

curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list

apt-get update -y && \
apt-get install ngrok

apt install python3
apt install pipenv

pipenv shell
pipenv install

# Start the first tmux session for running the Flask application
tmux new-session -d -s eval_app 'python3 eval_tool.py'

# Wait for Flask to start
sleep 5

# Start the second tmux session for ngrok
tmux new-session -d -s eval_ngrok "ngrok authtoken $FLASK_AT && ngrok http --url=still-frog-guided.ngrok-free.app 19198"

# Confirm both sessions have been started
echo "Flask app started in tmux session 'eval_app'."
echo "ngrok started in tmux session 'eval_ngrok'."