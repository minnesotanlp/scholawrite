import datasets
import pandas as pd
import matplotlib.pyplot as plt

dataset = datasets.load_from_disk("dataset_savefile.hf")
# Assuming dataset is a dictionary containing "train" and "test" dataframes
train_data = dataset["train"].to_pandas()
test_data = dataset["test"].to_pandas()

# Count the occurrences of each writing intention in the train and test datasets
train_counts = train_data['writing_intention'].value_counts()
test_counts = test_data['writing_intention'].value_counts()

# Plotting the bar graphs for train and test datasets
plt.figure(figsize=(10, 6))

plt.subplot(1, 2, 1)
train_counts.plot(kind='bar')
plt.title('Train Data - Writing Intention Distribution')
plt.xlabel('Writing Intention')
plt.ylabel('Frequency')
plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels by 45 degrees

plt.subplot(1, 2, 2)
test_counts.plot(kind='bar')
plt.title('Test Data - Writing Intention Distribution')
plt.xlabel('Writing Intention')
plt.ylabel('Frequency')
plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels by 45 degrees

plt.tight_layout()
plt.savefig("test.png")
plt.show()




