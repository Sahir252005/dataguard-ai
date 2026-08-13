import json

import faiss
from sentence_transformers import SentenceTransformer


INDEX_FILE = "data/incidents.index"
METADATA_FILE = "data/metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"


print("Loading model...")
model = SentenceTransformer(MODEL_NAME)

print("Loading FAISS index...")
index = faiss.read_index(INDEX_FILE)

with open(METADATA_FILE, "r", encoding="utf-8") as file:
    documents = json.load(file)


query = input("\nEnter incident/query:\n> ")

query_embedding = model.encode(
    [query],
    convert_to_numpy=True,
    normalize_embeddings=True
).astype("float32")


scores, indices = index.search(query_embedding, 3)


print("\nTop 3 Similar Incidents:\n")

for rank, (score, idx) in enumerate(
    zip(scores[0], indices[0]), start=1
):
    incident = documents[idx]

    print(f"{rank}. {incident['incident_id']}")
    print(f"   Similarity: {score:.4f}")

    # Print the first part of the retrieved incident
    text = incident["text"]

    lines = text.splitlines()

    for line in lines:
        if line.strip():
            print(f"   {line.strip()}")
            break

    print()