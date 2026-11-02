import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library
import pickle
from sentence_transformers import SentenceTransformer

sentence = "Artificial Intelligence"

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode([sentence])

# OpenAlex Matching
with open('openalex.pickle', 'rb') as handle:
    openalex = pickle.load(handle)

D, I = openalex["index"].search(embeddings, k=1)

print(D)

for i in I[0]:
    print(openalex["sentences"][i])