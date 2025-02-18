import os
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, ConfusionMatrixDisplay, classification_report
import matplotlib.pyplot as plt

#fname = "scholawrite/meta_inference/llama3b_meta_instruction/llama3_meta_class_result.csv"
#fname = "scholawrite/meta_inference/llama8b_meta_instruction/llama8_meta_class_result.csv"
#fname = "scholawrite/scholawrite_finetune/llama3b_scholawrite_finetune/llama3_SW_class_result.csv"
fname = "scholawrite/scholawrite_finetune/llama8b_scholawrite_finetune/llama8_SW_class_result.csv"
#fname = "scholawrite/gpt4o/gpt4o_class_result.csv"
#fname = "ROBERTA_BASE_run_final.csv"
#fname = "BERT_run_final.csv"
#fname = "ROBERTA_run_final.csv"
#fname = "BERT_BASE_run_final.csv"

fnames = [
"scholawrite/meta_inference/llama3b_meta_instruction/llama3_meta_class_result.csv",
"scholawrite/meta_inference/llama8b_meta_instruction/llama8_meta_class_result.csv",
"scholawrite/scholawrite_finetune/llama3b_scholawrite_finetune/llama3_SW_class_result.csv",
"scholawrite/scholawrite_finetune/llama8b_scholawrite_finetune/llama8_SW_class_result.csv",
"scholawrite/gpt4o/gpt4o_class_result.csv",
"ROBERTA_BASE_run_final.csv",
"BERT_run_final.csv",
"ROBERTA_run_final.csv",
"BERT_BASE_run_final.csv"
]

def calculate_metrics(eval_df):

  y_true = eval_df["label"]

  try:
    y_pred = eval_df["predicted"]
  except:
    y_pred = eval_df["predicted_label"]

  accuracy = accuracy_score(y_true, y_pred)

  labels = sorted(eval_df["label"].unique())
  conf_mat = confusion_matrix(y_true, y_pred, labels=labels)

  disp = ConfusionMatrixDisplay(confusion_matrix=conf_mat, display_labels=labels)

  disp.plot(cmap=plt.cm.Blues)

  plt.xticks(rotation=-45, ha='left')
  plt.tight_layout()
  plt.xlabel("")
  plt.ylabel("")
  plt.savefig(f"conf_mats/confusion_matrix_{os.path.basename(fname)}.pdf", format="pdf")
  plt.show()

  macro_f1 = f1_score(y_true, y_pred, average="macro")
  micro_f1 = f1_score(y_true, y_pred, average="micro")
  report = classification_report(y_true, y_pred)

  print("macro f1", macro_f1)
  print("micro f1", micro_f1)
  print("acc", accuracy)
  print('report', report)

for fname in fnames:
  df = pd.read_csv(fname)
  calculate_metrics(df)
