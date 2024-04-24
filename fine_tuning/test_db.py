from pymongo import MongoClient
import pandas as pd

port = 5001

client = MongoClient("localhost", port)
data = client["dataset_db"]["fine_tuning"]
query = {}

cursor = data.find(query)

df = pd.DataFrame(list(cursor))
print(df.head())
print(df.columns)
print("end")