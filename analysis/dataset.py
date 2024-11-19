from pymongo import MongoClient
import pandas as pd
from datasets import load_dataset, concatenate_datasets

class KeystrokeDataset:
  def __init__(self):
    try: 
        client = MongoClient("localhost", 27017)
        print("Connected successfully!!!") 
    except:
        print("Could not connect to MongoDB")

    self.db = client["flask_db"]
    ds = load_dataset("minnesotanlp/scholawrite")
    ds = concatenate_datasets([ds["train"], ds["test"]])
    self.ds = ds.to_pandas()
    self.ds.loc[self.ds["project"] == "6578ec8845504beacf9d3dc7", "project"] = "6500d748909490ecba83e811"

    print(self.ds["label"].unique())

  def get_annotations(self, annotator_email="update"):
    query = {"annotatorEmail": annotator_email}
    cursor = self.db.annotation.find(query)

    #return pd.DataFrame(list(cursor))
    return self.ds

  def get_visual_data(self, project_id):
    query = {"project": project_id}
    #cursor = self.db.activity.find(query)
    cursor = self.db.visual_data.find(query)

    #return pd.DataFrame(list(cursor))
    return self.ds

  def get_dataset_dump(self):
    query = {}
    #cursor = self.db.activity.find(query)
    cursor = self.db.visual_data.find(query)

    return pd.DataFrame(list(cursor))
    return self.ds