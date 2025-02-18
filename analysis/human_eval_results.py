import seaborn as sns
import pandas as pd 
import matplotlib.pyplot as plt 

# Data from the tables
data = {
    "Seed": ["Seed 1", "Seed 1", "Seed 1", 
             "Seed 2", "Seed 2", "Seed 2", 
             "Seed 3", "Seed 3", "Seed 3", 
             "Seed 4", "Seed 4", "Seed 4"],
    "Model": ["Llama-8B-SW", "Llama-8B-Instruct", "GPT4o"] * 4,
    "Lexical Diversity": [0.4985, 0.2268, 0.3405,
                          0.4262,  0.23, 0.3113,
                          0.457, 0.1784, 0.3093,
                          0.359, 0.1824, 0.3139],
    "Cosine Similarity": [0.8197, 0.4494, 0.6516,
                          0.8644,  0.8319, 0.6585,
                          0.7772,  0.8367, 0.4037,
                          0.2147,  0.5353, 0.6500], 
    "Intention Coverage": [10,  8, 5, 
                           11,  7, 6, 
                           7, 6, 11, 
                           11, 6, 7]
}

# Create a dataframe
df = pd.DataFrame(data)

hatches_e = {
    "Llama-8B-SW": "/",       # Diagonal lines
    "Llama-8B-Instruct": "o", # Dots
    "GPT4o": "+"              # Plus signs
}

# Plot 1: Lexical Diversity
plt.figure(figsize=(8, 4))
barplot = sns.barplot(data=df, x="Seed", y="Lexical Diversity", hue="Model", palette="husl")

# Apply hatches based on the hue (Model)
model_order = df["Model"].unique()  # Get the order of the models
for patch, hue_value in zip(barplot.patches, [h for h in model_order for _ in range(len(df["Seed"].unique()))]):
    patch.set_hatch(hatches_e[hue_value])

plt.ylabel(None)
plt.xlabel(None)  # Hide the xlabel title
plt.xticks(fontsize=27)
plt.yticks(fontsize=20)
plt.legend([], [], frameon=False)  # Remove legend
plt.tight_layout()
plt.savefig('lexical_all_no_legend.pdf', format='pdf', bbox_inches='tight')


# Plot 2: Cosine Similarity

plt.figure(figsize=(12, 5))
barplot = sns.barplot(data=df, x="Seed", y="Cosine Similarity", hue="Model", palette="husl")

model_order = df["Model"].unique()  # Get the order of the models
for patch, hue_value in zip(barplot.patches, [h for h in model_order for _ in range(len(df["Seed"].unique()))]):
    patch.set_hatch(hatches_e[hue_value])
    
plt.ylabel(None)
# plt.ylabel("Topic Consistency", fontsize=20)
plt.xlabel(None)  # Hide the xlabel title
plt.xticks(fontsize=27)
plt.yticks(fontsize=20)
plt.legend(bbox_to_anchor=(0.05, 1), fontsize=20, ncol=3)
# plt.legend([], [], frameon=False)  # Remove legend
# plt.tight_layout()
plt.savefig('topic_all_no_legend.pdf', format='pdf', bbox_inches='tight')


# Plot 3: Intention Coverage

plt.figure(figsize=(8, 4))
barplot = sns.barplot(data=df, x="Seed", y="Intention Coverage", hue="Model", palette="husl")

model_order = df["Model"].unique()  # Get the order of the models
for patch, hue_value in zip(barplot.patches, [h for h in model_order for _ in range(len(df["Seed"].unique()))]):
    patch.set_hatch(hatches_e[hue_value])
    
plt.ylabel(None)
# plt.ylabel("Intention Coverage (Among 15)", fontsize=20)
plt.xlabel(None)  # Hide the xlabel title
plt.xticks(fontsize=27)
plt.yticks(fontsize=20)
plt.legend([], [], frameon=False)  # Remove legend
plt.tight_layout()
plt.savefig('intention_all_no_legend.pdf', format='pdf', bbox_inches='tight')

plt.show()
