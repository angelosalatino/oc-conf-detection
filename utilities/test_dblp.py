import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library
import pickle
from sentence_transformers import SentenceTransformer

sentence = "5th International Workshop on Scientific Knowledge: Representation, Discovery, and Assessment"

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode([sentence])

# DBLP Matching
with open('DBLP.pickle', 'rb') as handle:
    dblp_confs = pickle.load(handle)

D, I = dblp_confs["index"].search(embeddings, k=1)

print(D)

for i in I[0]:
    print(dblp_confs["sentences"][i])
    