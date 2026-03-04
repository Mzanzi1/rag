# C:\AI Projects\rag2\sql_toqdrant_chunked.py
import sys
import os
import re
import logging
import uuid
import mysql.connector
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv

# Local imports
try:
    from chunking import TokenAwareChunker
except ImportError:
    logging.error("❌ Could not find chunking.py. Ensure it is in the same directory.")
    sys.exit(1)

# ============================================================================
# 1. PATH & ENVIRONMENT SETUP
# ============================================================================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, '..'))
load_dotenv(os.path.join(project_root, '.env'))

# ============================================================================
# 2. CONFIGURATION
# ============================================================================
BATCH_SIZE = 50
COLLECTION_NAME = "email_collection"
MODEL_PATH = os.path.join(project_root, "models", "all-MiniLM-L6-v2")
VECTOR_SIZE = 384  # Specific to all-MiniLM-L6-v2

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ============================================================================
# 3. HYBRID CLEANING LOGIC
# ============================================================================
def hybrid_clean(text: str) -> str:
    if not text: return ""

    # 1. Improved Regex: Handles extra spaces and the "samsung disclaimer" header
    # This pattern is more flexible with whitespace \s*
    cfo_patterns = [
        r"samsung\s*disclaimer\s*:.*",  # Catch the header and everything after
        r"all\s*forms\s*of\s*communications.*?samsung\s*cfo.*",
        r"reliance\s*on\s*any\s*communications.*?samsung\s*cfo.*",
        r"visit\s*us\s*at\s*http\s*:\s*/\s*/\s*www\s*\.\s*samsung\s*\.\s*com"
        r"- - - - - - - - - original message - - - - - - - - -.*",
        r"sender\s*:\s*.*?\n", # Removes the sender lines
    ]

    # Use lowercase for matching to handle all variants
    temp_text = text.lower()
    for pattern in cfo_patterns:
        temp_text = re.sub(pattern, "", temp_text, flags=re.IGNORECASE | re.DOTALL)

    # 2. Split at signature markers (Now space-insensitive)
    markers = ["best regards", "thanks & regards", "thanks and regards", "regards,", "thank you and best regards"]
    for m in markers:
        if m in temp_text:
            temp_text = temp_text.split(m)[0]
            break

    return temp_text.strip()

# ============================================================================
# 4. DATABASE CONNECTION
# ============================================================================
def get_mysql_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            use_pure=True,
            connection_timeout=30
        )
        return conn
    except mysql.connector.Error as err:
        logging.error(f"❌ MySQL Connection Failed: {err}")
        return None


# ============================================================================
# 5. MIGRATION LOGIC
# ============================================================================
def migrate():
    logging.info(f"🚀 Starting Migration (Collection: {COLLECTION_NAME})")

    db = get_mysql_connection()
    if not db: return

    cursor = db.cursor(dictionary=True)
    q_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

    # FIX 1: Auto-recreate collection if missing (Fixes 404)
    if not q_client.collection_exists(COLLECTION_NAME):
        logging.info(f"✨ Creating missing collection: {COLLECTION_NAME}")
        q_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    try:
        model = SentenceTransformer(MODEL_PATH)
        chunker = TokenAwareChunker(MODEL_PATH)
    except Exception as e:
        logging.error(f"❌ Resource Load Error: {e}")
        return

    # FIX 2: String-based Checkpoint logic
    last_uid = ""
    checkpoint_file = os.path.join(project_root, "migration_checkpoint.txt")
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            last_uid = f.read().strip()

    # Get total count
    if last_uid == "":
        cursor.execute("SELECT COUNT(*) as total FROM emailcontent")
    else:
        cursor.execute("SELECT COUNT(*) as total FROM emailcontent WHERE UID > %s", (last_uid,))

    total_records = cursor.fetchone()['total']
    if total_records == 0:
        logging.info("✨ No new data to process.")
        return

    pbar = tqdm(total=total_records, desc="🧹 Cleaning & Migrating")

    while True:
        if last_uid == "":
            cursor.execute("""
                SELECT UID, plaintext, subject, email_date, operator, country, sub AS subs 
                FROM emailcontent ORDER BY UID ASC LIMIT %s
            """, (BATCH_SIZE,))
        else:
            cursor.execute("""
                SELECT UID, plaintext, subject, email_date, operator, country, sub AS subs 
                FROM emailcontent WHERE UID > %s ORDER BY UID ASC LIMIT %s
            """, (last_uid, BATCH_SIZE))

        rows = cursor.fetchall()
        if not rows: break

        all_chunks_text = []
        all_payloads = []

        for row in rows:
            raw_text = row['plaintext'] or ""
            cleaned_text = hybrid_clean(raw_text)

            if len(cleaned_text) < 20:
                last_uid = row['UID']
                continue

            # FIX 3: Recursive Chunking to avoid 512-token limit errors
            # If your chunker fails, this ensures we don't send 792 tokens to the model
            chunks = chunker.split_text(cleaned_text)

            for i, chunk_text in enumerate(chunks):
                # Hard limit for model safety
                safe_text = chunk_text[:2000]  # Rough character limit to prevent overflow
                all_chunks_text.append(safe_text)
                all_payloads.append({
                    "original_uid": row['UID'],
                    "subject": row['subject'],
                    "body": safe_text,
                    "email_date": str(row['email_date']),
                    "operators": [row['operator']] if row['operator'] else [],
                    "countries": [row['country']] if row['country'] else [],
                    "subs": [row['subs']] if row['subs'] else []
                })
            last_uid = row['UID']

        if all_chunks_text:
            vectors = model.encode(all_chunks_text, batch_size=32, show_progress_bar=False)
            points = []
            for idx, (vec, payload) in enumerate(zip(vectors, all_payloads)):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{payload['original_uid']}_{idx}"))
                points.append(PointStruct(id=point_id, vector=vec.tolist(), payload=payload))

            q_client.upsert(collection_name=COLLECTION_NAME, points=points)

        with open(checkpoint_file, "w") as f:
            f.write(str(last_uid))

        pbar.update(len(rows))

    db.close()
    logging.info("✅ Migration complete. Collection is fresh and clean.")


if __name__ == "__main__":
    migrate()
