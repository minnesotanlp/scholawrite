"""
 Analysis of intentions during inference
"""

import os

import pandas as pd
from datasets import load_dataset
from huggingface_hub import login
from dotenv import load_dotenv
from pylatexenc.latex2text import LatexNodes2Text
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt_tab')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('punkt')
nltk.download('stopwords')

stop_words = set(stopwords.words('english'))

load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
login(token=HUGGINGFACE_TOKEN)

full_ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")

ds = full_ds["train"]
df = pd.DataFrame(ds)

def calculate_lexical_diverse(text):
  try:
    text = LatexNodes2Text().latex_to_text(text)
    tokens = word_tokenize(text)

    new_tokens = []
    for word in tokens:
        if word.isalnum() and (word not in stop_words):
            new_tokens.append(word.lower())

    result = len(set(new_tokens)) / len(new_tokens)
    return result
  except:
     return None

df["lexical_diversity"] = df["after text"].apply(lambda x: calculate_lexical_diverse(x))

"""
label
Citation Integration    0.716631
Clarity                 0.635159
Coherence               0.651811
Cross-reference         0.614943
Fluency                 0.636568
Idea Generation         0.666978
Idea Organization       0.676632
Linguistic Style        0.643151
Macro Insertion         0.784932
Object Insertion        0.600461
Scientific Accuracy     0.645052
Section Planning        0.636674
Structural              0.627357
Text Production         0.649310
Visual Formatting       0.633074
Name: lexical_diversity, dtype: float64

OVERALL:
0.6454166215622221
"""


