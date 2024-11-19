import pandas as pd
from statsmodels.stats.inter_rater import fleiss_kappa

df = pd.read_csv("Iterative_prediction_eval.csv")

annotations = ['Flow', 'Accuracy', 'Fluency']

df[annotations] = df[annotations].apply(lambda row: row.value_counts(), axis=1)

average_L_per_seed = df.groupby('Seed')['L_count'].mean().reset_index()
print("Average occurrences of 'L' for each seed:")
print(average_L_per_seed)

df_kappa = df[annotations].replace({'G': 0, 'L': 1})

kappa_input = df_kappa.apply(lambda row: row.value_counts().reindex([0, 1], fill_value=0).values, axis=1).tolist()

kappa_input = pd.DataFrame(kappa_input, columns=[0, 1])

kappa_score = fleiss_kappa(kappa_input, method='fleiss')

print("\nFleiss' Kappa (Inter-Annotator Agreement):")
print(kappa_score)