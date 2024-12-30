#!/bin/bash

pipenv install

# Start the Flask application in a tmux session
tmux new-session -d -s eval_app "pipenv run python3 eval_tool.py"

# Wait for Flask to start
sleep 5

# Start ngrok in another tmux session
tmux new-session -d -s eval_ngrok "ngrok --config ./ngrok.yml http --url=still-frog-guided.ngrok-free.app 12345"

echo "Flask app started in tmux session 'eval_app'."
echo "ngrok started in tmux session 'eval_ngrok'."
