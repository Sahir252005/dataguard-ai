import json
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INPUT_FILE = "data/prepared.jsonl"
INDEX_FILE = "data/incidents.index"
METADATA_FILE = "data/metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"


print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

documents = []
texts = []

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    for line in file:
        item = json.loads(line)

        documents.append(item)
        texts.append(item["text"])

print(f"Loaded {len(texts)} incidents.")

print("Generating embeddings...")
embeddings = model.encode(
    texts,
    convert_to_numpy=True,
    normalize_embeddings=True
)

embeddings = embeddings.astype("float32")

dimension = embeddings.shape[1]

print(f"Embedding dimension: {dimension}")

index = faiss.IndexFlatIP(dimension)

index.add(embeddings)

faiss.write_index(index, INDEX_FILE)

with open(METADATA_FILE, "w", encoding="utf-8") as file:
    json.dump(
        documents,
        file,
        ensure_ascii=False,
        indent=2
    )

print(f"FAISS index contains {index.ntotal} incidents.")
print("Index created successfully.")