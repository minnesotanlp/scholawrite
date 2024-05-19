import json
import numpy as np
import matplotlib.pyplot as plt

file = "output/trainer_state.json"
#file = "example.txt"

with open(file, 'r') as file:
  output = json.load(file)

log = output["log_history"]

x_train = []
y_train = []

x_eval = []
y_eval = []

for entry in log:
  if ("loss" in entry.keys()):
    x_train.append(entry["epoch"])
    y_train.append(entry["loss"])
  elif ("eval_loss" in entry.keys()):
    x_eval.append(entry["epoch"])
    y_eval.append(entry["eval_loss"])

fig,ax = plt.subplots(1)
ax.set_title("Llama 3 training")
ax.plot(x_train, y_train, label="train loss", color="blue")
ax.plot(x_eval, y_eval, label="eval loss", color="orange")
fig.legend()
fig.savefig("loss.png")



