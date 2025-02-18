import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

df = pd.read_csv("BERT_run_final.csv")

def calculate_metrics(eval_df):

  y_true = eval_df["label"]
  y_pred = eval_df["predicted_label"]

  accuracy = accuracy_score(y_true, y_pred)

  print("acc", accuracy)

calculate_metrics(df)