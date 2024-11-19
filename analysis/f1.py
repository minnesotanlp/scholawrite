import pandas as pd
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt

plt.rcParams.update({'font.size': 16})

df = pd.read_csv("intention_class_eval.csv")

le = LabelEncoder()

print(df.columns)

labs1 = df["label"].unique().tolist()
labs2 = df["predicted_label"].unique().tolist()

labs = list(set(labs1 + labs2))
le.fit_transform(labs)

df["label"] = le.transform(df["label"])
df["predicted_label"] = le.transform(df["predicted_label"])

report = classification_report(df['label'], df['predicted_label'], target_names=le.classes_, output_dict=True)

df = pd.DataFrame(report).T

df2 = pd.read_csv("gpt4o-class-result.csv").T
df2 = df2.iloc[1:]
df2.columns = ["precision", "recall", "f1 - GPT-4o", "support"]

#print(pd.concat((df["f1-score"], df2["f1 - GPT-4o"]), axis=1).to_latex(float_format="%.2f"))
df_c  = pd.concat((df["f1-score"], df2["f1 - GPT-4o"]), axis=1)

filter = ["nan", "No Label", "Textual Style"]

df_c = df_c[~df_c.index.isin(filter)]
df_c = df_c[::-1]
df_c = df_c[3:]

print(df_c.head())
print(df_c.index)

plt.figure(figsize=(8, 6))

# Define the positions of the bars
bar_width = 0.35
index = range(len(df_c))

# Plot the bars
plt.barh(index, df_c['f1-score'], height=bar_width, label='Llama 3.2', align='center')
plt.barh([i + bar_width for i in index], df_c['f1 - GPT-4o'], height=bar_width, label='GPT4o', align='center')

# Add labels, title, and legend
plt.xlabel('F1')
plt.ylabel('Label')
plt.xscale('log')
#plt.axhline(y=index[3]-0.25, color='gray', linestyle='--', linewidth=2)
#plt.title('F1 scores for Intention Classification')
plt.yticks([i + bar_width / 2 for i in index], df_c.index)  # Align x-ticks in the center
plt.legend()

# Display the plot
plt.legend(loc='center right', bbox_to_anchor=(1, 0.6))
plt.tight_layout()
#plt.show()
plt.savefig("llama_vs_gpt.pdf", format="pdf")
