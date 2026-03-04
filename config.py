# C:\AI Projects\rag2\config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# --- Dynamic Path Handling ---
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load .env from root
load_dotenv(PROJECT_ROOT / ".env")

# --- Model & Database ---
# Scout Model (Bi-Encoder)
MODEL_PATH = str(PROJECT_ROOT / "models" / "paraphrase-multilingual-mpnet-base-v2")

# Judge Model (Cross-Encoder / Reranker)
# Using your confirmed folder name: ms-marco-MiniLM-L6-v2
RERANKER_PATH = str(PROJECT_ROOT / "models" / "ms-marco-MiniLM-L6-v2")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "email_collection")

# --- Search Tuning ---
SEARCH_TOP_K = 25       # How many candidates the Scout finds
RERANK_TOP_K = 5        # How many finalists the Judge selects
SCORE_THRESHOLD = 0.40  # Initial vector threshold
BODY_TRUNCATE = 2500

# --- Agent API ---
AGENT_API_URL = os.getenv("QDRANT_BUILDER_URL")
AGENT_API_KEY = os.getenv("QDRANT_BUILDER_API")
AGENT_TIMEOUT = 120

AGENTS = [
    {"name": "facts", "focus": "Extract technical data, Ticket IDs, and operator status."},
    {"name": "actions", "focus": "Identify blockers, pending feedback, and next steps."},
    {"name": "timeline", "focus": "Sequence events and find approval dates."}
]

def validate():
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ SCOUT MODEL NOT FOUND AT: {MODEL_PATH}")
    if not os.path.exists(RERANKER_PATH):
        print(f"⚠️ RERANKER MODEL NOT FOUND AT: {RERANKER_PATH}")
    if not AGENT_API_URL or not AGENT_API_KEY:
        print("❌ MISSING API CREDENTIALS IN .ENV")

if __name__ == "__main__":
    validate()
    print(f"✅ Config Loaded. Root: {PROJECT_ROOT}")
