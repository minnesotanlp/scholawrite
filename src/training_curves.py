import pandas as pd
import matplotlib.pyplot as plt

log_file = "results/unsloth/Llama-3.2-1B-bnb-4bit_run_2024-10-06 04:27:15.452895_intention_bt/trainer_state.json"

logs = pd.read_json(log_file)

print(logs.head())

plt.figure(figsize=(10, 5))
plt.plot(logs['step'], logs['loss'], label='Training Loss')
plt.xlabel('Steps')
plt.ylabel('Loss')
plt.title('Training Loss Over Time')
plt.legend()
plt.show()

plt.figure(figsize=(10, 5))
plt.plot(logs['step'], logs['eval_accuracy'], label='Validation Accuracy', color='orange')
plt.xlabel('Steps')
plt.ylabel('Accuracy')
plt.title('Validation Accuracy Over Time')
plt.legend()
plt.show()