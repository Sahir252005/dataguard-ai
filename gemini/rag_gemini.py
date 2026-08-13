import os
import json
import faiss

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your .env file."
    )

MODEL_NAME = "all-MiniLM-L6-v2"

INDEX_FILE = "data/incidents.index"
METADATA_FILE = "data/metadata.json"
ORIGINAL_DATASET = "data/incidents.jsonl"


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(MODEL_NAME)


# ============================================================
# LOAD FAISS INDEX
# ============================================================

print("Loading FAISS index...")

index = faiss.read_index(INDEX_FILE)


# ============================================================
# LOAD ORIGINAL INCIDENT DATA
# ============================================================

print("Loading incident data...")

incidents = {}

with open(ORIGINAL_DATASET, "r", encoding="utf-8") as file:

    for line in file:

        incident = json.loads(line)

        incidents[incident["incident_id"]] = incident


# ============================================================
# LOAD FAISS METADATA
# ============================================================

with open(METADATA_FILE, "r", encoding="utf-8") as file:

    metadata = json.load(file)


# ============================================================
# CONNECT TO GEMINI
# ============================================================

print("Connecting to Gemini...")

client = genai.Client(api_key=API_KEY)


# ============================================================
# RAG SEARCH
# ============================================================

def search_incidents(query, top_k=3):

    query_embedding = embedding_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(
        query_embedding,
        top_k
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):

        incident_id = metadata[idx]["incident_id"]

        results.append({
            "incident_id": incident_id,
            "similarity": float(score),
            "incident": incidents[incident_id]
        })

    return results


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(query, results):

    historical_context = ""

    for i, result in enumerate(results, start=1):

        historical_context += f"""
============================================================
HISTORICAL INCIDENT {i}
============================================================

Incident ID:
{result["incident_id"]}

Similarity Score:
{result["similarity"]:.4f}

Full Incident Record:
{json.dumps(result["incident"], indent=2)}
"""


    prompt = f"""
You are a Data Engineering Incident Analysis Assistant.

Your task is to analyze the current production anomaly using
the historical incidents retrieved from our internal
incident knowledge base.

IMPORTANT RULES:

1. Use the historical incidents as supporting evidence.
2. Do NOT blindly copy the root cause from a historical incident.
3. The current incident may have a different root cause.
4. Clearly distinguish evidence from inference.
5. Do not invent metrics, logs, causes, or other facts.
6. If the available information is insufficient, explicitly say so.
7. Give practical recommendations for a data engineering team.

============================================================
CURRENT INCIDENT
============================================================

{query}


============================================================
RETRIEVED HISTORICAL INCIDENTS
============================================================

{historical_context}


============================================================
REQUIRED OUTPUT
============================================================

Analyze the current incident using the following structure:

1. Problem Summary

2. Detected Anomaly

3. Most Likely Root Cause

4. Supporting Evidence

5. Business / System Impact

6. Recommended Resolution

7. Prevention Measures

8. Similar Historical Incidents

For section 8, list each retrieved incident with:

- Incident ID
- Why it is relevant
- Important similarity to the current incident

Keep the explanation technically accurate, concise,
and easy for a data engineer to understand.
"""


    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return response.text


# ============================================================
# MAIN PROGRAM
# ============================================================

query = input(
    "\nDescribe the current production incident:\n> "
)


# ------------------------------------------------------------
# Step 1: RAG retrieval
# ------------------------------------------------------------

print("\nSearching incident knowledge base...")

results = search_incidents(query)


# ------------------------------------------------------------
# Step 2: Display Top 3
# ------------------------------------------------------------

print("\nTop 3 Retrieved Incidents:\n")

for result in results:

    print(
        f"{result['incident_id']} "
        f"(similarity: {result['similarity']:.4f})"
    )


# ------------------------------------------------------------
# Step 3: Send RAG context to Gemini
# ------------------------------------------------------------

print("\nSending retrieved context to Gemini...")


analysis = analyze_with_gemini(
    query,
    results
)


# ------------------------------------------------------------
# Step 4: Display Gemini result
# ------------------------------------------------------------

print("\n")

print("=" * 70)

print("GEMINI INCIDENT ANALYSIS")

print("=" * 70)

print()

print(analysis)

print()

print("=" * 70)