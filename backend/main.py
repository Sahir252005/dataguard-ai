import os
import json
import time
import faiss

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types

from pypdf import PdfReader
from docx import Document

from io import BytesIO
from pydantic import BaseModel


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

GEMINI_MODEL = "gemini-3.1-flash-lite"
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_FILE = BASE_DIR / "data" / "incidents.index"
METADATA_FILE = BASE_DIR / "data" / "metadata.json"
ORIGINAL_DATASET = BASE_DIR / "data" / "incidents.jsonl"
MAX_QUERY_CHARS = 12000


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Data Engineering Incident Analyzer",
    description="RAG + Gemini Incident Analysis API",
    version="1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    MODEL_NAME
)

print("Embedding model loaded.")


# ============================================================
# LOAD FAISS INDEX
# ============================================================

print("Loading FAISS index...")

index = faiss.read_index(
    INDEX_FILE
)

print(
    f"FAISS index loaded. Size: {index.ntotal}"
)


# ============================================================
# LOAD INCIDENT DATA
# ============================================================

print("Loading incident data...")

incidents = {}

with open(
    ORIGINAL_DATASET,
    "r",
    encoding="utf-8"
) as file:

    for line in file:

        if not line.strip():
            continue

        incident = json.loads(line)

        incidents[
            incident["incident_id"]
        ] = incident


print(
    f"Loaded {len(incidents)} incidents."
)


# ============================================================
# LOAD METADATA
# ============================================================

print("Loading metadata...")

with open(
    METADATA_FILE,
    "r",
    encoding="utf-8"
) as file:

    metadata = json.load(file)

print("Metadata loaded.")


# ============================================================
# GEMINI
# ============================================================

print("Connecting to Gemini...")

client = genai.Client(
    api_key=API_KEY
)

print("Gemini connected.")


# ============================================================
# DOCUMENT TEXT EXTRACTION
# ============================================================

async def extract_text(file: UploadFile):

    filename = (
        file.filename or ""
    ).lower()

    content = await file.read()


    # --------------------------------------------------------
    # TXT
    # --------------------------------------------------------

    if filename.endswith(".txt"):

        try:

            return content.decode(
                "utf-8"
            )

        except UnicodeDecodeError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not decode TXT file "
                    "as UTF-8."
                )
            )


    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    elif filename.endswith(".pdf"):

        try:

            pdf = PdfReader(
                BytesIO(content)
            )

            pages = []

            for page in pdf.pages:

                page_text = (
                    page.extract_text()
                    or ""
                )

                if page_text.strip():

                    pages.append(
                        page_text
                    )

            return "\n".join(pages)

        except Exception as e:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Could not read PDF file: {str(e)}"
                )
            )


    # --------------------------------------------------------
    # DOCX
    # --------------------------------------------------------

    elif filename.endswith(".docx"):

        try:

            document = Document(
                BytesIO(content)
            )

            paragraphs = []

            for paragraph in document.paragraphs:

                text = paragraph.text.strip()

                if text:

                    paragraphs.append(
                        text
                    )

            return "\n".join(
                paragraphs
            )

        except Exception as e:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Could not read DOCX file: {str(e)}"
                )
            )


    # --------------------------------------------------------
    # UNSUPPORTED
    # --------------------------------------------------------

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Use TXT, PDF, or DOCX."
            )
        )


# ============================================================
# CLEAN QUERY
# ============================================================

def clean_query(text):

    text = text.strip()

    if len(text) > MAX_QUERY_CHARS:

        print(
            f"Document is large "
            f"({len(text)} chars). "
            f"Limiting to {MAX_QUERY_CHARS} chars."
        )

        text = text[
            :MAX_QUERY_CHARS
        ]

    return text


# ============================================================
# RAG SEARCH
# ============================================================

def search_incidents(
    query,
    top_k=3
):

    query_embedding = (
        embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        .astype("float32")
    )


    scores, indices = index.search(
        query_embedding,
        top_k
    )


    results = []

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        if idx < 0:
            continue

        incident_id = metadata[
            idx
        ]["incident_id"]


        if incident_id not in incidents:
            continue


        results.append({

            "incident_id":
                incident_id,

            "similarity":
                round(
                    float(score),
                    4
                ),

            "incident":
                incidents[
                    incident_id
                ]

        })


    return results


# ============================================================
# COMPACT HISTORICAL CONTEXT
# ============================================================

def build_historical_context(
    results
):

    context_parts = []

    for i, result in enumerate(
        results,
        start=1
    ):

        incident = result[
            "incident"
        ]

        compact_incident = {

            "incident_id":
                result["incident_id"],

            "similarity":
                result["similarity"],

            "anomaly":
                incident.get(
                    "anomaly",
                    {}
                ),

            "root_cause":
                incident.get(
                    "root_cause",
                    {}
                ),

            "impact":
                incident.get(
                    "impact",
                    {}
                ),

            "resolution":
                incident.get(
                    "resolution",
                    {}
                ),

            "prevention":
                incident.get(
                    "prevention",
                    []
                )

        }

        context_parts.append(
            f"HISTORICAL INCIDENT {i}:\n"
            +
            json.dumps(
                compact_incident,
                separators=(
                    ",",
                    ":"
                )
            )
        )

    return "\n\n".join(
        context_parts
    )


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(
    query,
    results
):

    historical_context = (
        build_historical_context(
            results
        )
    )


    prompt = f"""
You are a Data Engineering Incident Analysis Assistant.

Analyze the current production incident using the retrieved
historical incidents as evidence.

RULES:

- Do not invent facts.
- Do not blindly copy historical root causes.
- Clearly distinguish evidence from inference.
- Give practical resolution steps.
- Keep the answer concise.
- Mention historical Incident IDs when relevant.

CURRENT INCIDENT:

{query}

HISTORICAL INCIDENTS:

{historical_context}

Return the analysis using exactly these sections:

### 1. Problem Summary

### 2. Detected Anomaly

### 3. Most Likely Root Cause

### 4. Supporting Evidence

### 5. Business / System Impact

### 6. Recommended Resolution

### 7. Prevention Measures

### 8. Similar Historical Incidents
"""


    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=prompt,

        config=types.GenerateContentConfig(

            thinking_config=types.ThinkingConfig(
                thinking_level="minimal"
            ),

            max_output_tokens=800
        )
    )


    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )


    return response.text


# ============================================================
# CHAT REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    question: str

    incident: str

    similar_incidents: list = []


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "message":
            "Data Engineering Incident Analyzer API",

        "status":
            "running"

    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "rag_index_size":
            index.ntotal,

        "gemini":
            "connected"

    }


# ============================================================
# ANALYZE INCIDENT
# ============================================================

@app.post("/analyze")
async def analyze_incident(
    file: UploadFile = File(...)
):

    total_start = (
        time.perf_counter()
    )


    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file provided."
        )


    print("\n")
    print("=" * 60)

    print(
        f"ANALYZING: {file.filename}"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # EXTRACTION
    # --------------------------------------------------------

    extraction_start = (
        time.perf_counter()
    )


    query = await extract_text(
        file
    )


    extraction_time = (
        time.perf_counter()
        - extraction_start
    )


    if not query or not query.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract any "
                "text from the file."
            )
        )


    query = clean_query(
        query
    )


    print(
        f"Text extraction: "
        f"{extraction_time:.2f}s"
    )


    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    rag_start = (
        time.perf_counter()
    )


    results = search_incidents(
        query,
        top_k=3
    )


    rag_time = (
        time.perf_counter()
        - rag_start
    )


    print(
        f"RAG search: "
        f"{rag_time:.2f}s"
    )


    print(
        "\nTop 3 incidents:"
    )


    for result in results:

        print(
            f"  {result['incident_id']} "
            f"({result['similarity']})"
        )


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    gemini_start = (
        time.perf_counter()
    )


    try:

        analysis = (
            analyze_with_gemini(
                query,
                results
            )
        )

    except Exception as e:

        print(
            f"Gemini error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Gemini analysis failed: "
                f"{str(e)}"
            )
        )


    gemini_time = (
        time.perf_counter()
        - gemini_start
    )


    print(
        f"Gemini: "
        f"{gemini_time:.2f}s"
    )


    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_time = (
        time.perf_counter()
        - total_start
    )


    print("\n")
    print("=" * 60)

    print(
        "ANALYSIS PERFORMANCE"
    )

    print("=" * 60)

    print(
        f"File extraction : "
        f"{extraction_time:.2f}s"
    )

    print(
        f"RAG search      : "
        f"{rag_time:.2f}s"
    )

    print(
        f"Gemini          : "
        f"{gemini_time:.2f}s"
    )

    print(
        f"TOTAL           : "
        f"{total_time:.2f}s"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # SIMILAR INCIDENTS
    # --------------------------------------------------------

    similar_incidents = []

    for result in results:

        similar_incidents.append({

            "incident_id":
                result["incident_id"],

            "similarity":
                result["similarity"],

            "incident":
                result["incident"]

        })


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "filename":
            file.filename,

        "current_incident":
            query,

        "analysis":
            analysis,

        "similar_incidents":
            similar_incidents,

        "performance": {

            "extraction_seconds":
                round(
                    extraction_time,
                    2
                ),

            "rag_seconds":
                round(
                    rag_time,
                    2
                ),

            "gemini_seconds":
                round(
                    gemini_time,
                    2
                ),

            "total_seconds":
                round(
                    total_time,
                    2
                )

        }

    }


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat(
    request: ChatRequest
):

    start_time = (
        time.perf_counter()
    )


    # --------------------------------------------------------
    # VALIDATE QUESTION
    # --------------------------------------------------------

    question = (
        request.question.strip()
    )

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )


    # --------------------------------------------------------
    # CURRENT INCIDENT
    # --------------------------------------------------------

    incident_text = (
        request.incident.strip()
    )


    if len(incident_text) > MAX_QUERY_CHARS:

        incident_text = (
            incident_text[
                :MAX_QUERY_CHARS
            ]
        )


    # --------------------------------------------------------
    # HISTORICAL CONTEXT
    # --------------------------------------------------------

    historical_parts = []


    for item in request.similar_incidents:

        if not isinstance(
            item,
            dict
        ):
            continue


        incident = item.get(
            "incident",
            {}
        )


        if not isinstance(
            incident,
            dict
        ):
            continue


        compact = {

            "incident_id":
                item.get(
                    "incident_id"
                ),

            "similarity":
                item.get(
                    "similarity"
                ),

            "anomaly":
                incident.get(
                    "anomaly",
                    {}
                ),

            "root_cause":
                incident.get(
                    "root_cause",
                    {}
                ),

            "impact":
                incident.get(
                    "impact",
                    {}
                ),

            "resolution":
                incident.get(
                    "resolution",
                    {}
                ),

            "prevention":
                incident.get(
                    "prevention",
                    []
                )

        }


        historical_parts.append(
            json.dumps(
                compact,
                separators=(
                    ",",
                    ":"
                )
            )
        )


    historical_context = (
        "\n\n".join(
            historical_parts
        )
    )


    # --------------------------------------------------------
    # CHAT PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are DataGuard AI, an AI assistant for
data-engineering production incident investigation.

CURRENT INCIDENT:

{incident_text}

RELEVANT HISTORICAL INCIDENTS:

{historical_context}

USER QUESTION:

{question}

INSTRUCTIONS:

1. Answer the user's question directly.
2. If the user is greeting you or making casual conversation,
   respond naturally and briefly.
3. Do NOT repeat the complete incident analysis unless the
   user specifically asks for it.
4. Use historical incidents as supporting evidence when
   relevant.
5. Mention Incident IDs when useful.
6. Do not invent facts.
7. Clearly distinguish historical evidence from inference.
8. Keep responses concise and practical.
"""


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    try:

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),

                max_output_tokens=400
            )
        )

    except Exception as e:

        print(
            f"Chat Gemini error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Gemini chat failed: "
                f"{str(e)}"
            )
        )


    # --------------------------------------------------------
    # EMPTY RESPONSE
    # --------------------------------------------------------

    if not response.text:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini returned an empty response."
            )
        )


    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    total_time = (
        time.perf_counter()
        - start_time
    )


    print(
        f"Chat response: "
        f"{total_time:.2f}s"
    )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "question":
            question,

        "answer":
            response.text,

        "response_time_seconds":
            round(
                total_time,
                2
            )

    }