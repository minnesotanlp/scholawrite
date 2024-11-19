from pymongo import MongoClient
import pandas as pd

client = MongoClient("localhost", 27017)
db = client["flask_db"]

query = {}
cursor = db.visual_data.find(query)

df = pd.DataFrame(list(cursor))

print(df.head())