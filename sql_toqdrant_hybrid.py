import sys
import os
import re
import logging
import uuid
import mysql.connector
from typing import List
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, Distance, VectorParams, SparseVectorParams, SparseIndexParams
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
MODEL_PATH = os.path.join(project_root, "models", "paraphrase-multilingual-mpnet-base-v2")
VECTOR_SIZE = 768

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ============================================================================
# 3. UTILITY FUNCTIONS (Restored)
# ============================================================================
def hybrid_clean(text: str) -> str:
    if not text: return ""
    cfo_patterns = [
        r"samsung\s*disclaimer\s*:.*",
        r"all\s*forms\s*of\s*communications.*?samsung\s*cfo.*",
        r"reliance\s*on\s*any\s*communications.*?samsung\s*cfo.*",
        r"visit\s*us\s*at\s*http\s*:\s*/\s*/\s*www\s*\.\s*samsung\s*\.\s*com",
        r"- - - - - - - - - original message - - - - - - - - -.*",
        r"sender\s*:\s*.*?\n",
    ]
    temp_text = text
    for pattern in cfo_patterns:
        temp_text = re.sub(pattern, "", temp_text, flags=re.IGNORECASE | re.DOTALL)

    markers = ["best regards", "thanks & regards", "thanks and regards", "regards,", "thank you and best regards"]
    for m in markers:
        if m.lower() in temp_text.lower():
            temp_text = temp_text.split(m)[0]
            break
    return temp_text.strip()


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
# 4. MIGRATION LOGIC
# ============================================================================
def migrate():
    logging.info(f"🚀 Starting Hybrid Migration (Collection: {COLLECTION_NAME})")

    db = get_mysql_connection()
    if not db: return

    cursor = db.cursor(dictionary=True)
    q_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

    # Create Hybrid collection if missing
    if not q_client.collection_exists(COLLECTION_NAME):
        logging.info(f"✨ Creating Hybrid collection: {COLLECTION_NAME}")
        q_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=True)
                )
            }
        )

    try:
        model = SentenceTransformer(MODEL_PATH)
        chunker = TokenAwareChunker(MODEL_PATH)
    except Exception as e:
        logging.error(f"❌ Resource Load Error: {e}")
        return

    checkpoint_file = os.path.join(project_root, "migration_checkpoint.txt")
    last_uid = ""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            last_uid = f.read().strip()

    count_sql = "SELECT COUNT(*) as total FROM emailcontent" + (" WHERE UID > %s" if last_uid else "")
    cursor.execute(count_sql, (last_uid,) if last_uid else ())
    total_records = cursor.fetchone()['total']

    if total_records == 0:
        logging.info("✨ No new data to process.")
        return

    pbar = tqdm(total=total_records, desc="🧹 Hybrid Processing")

    while True:
        query_sql = f"SELECT UID, plaintext, subject, email_date, operator, country, sub FROM emailcontent {'WHERE UID > %s' if last_uid else ''} ORDER BY UID ASC LIMIT %s"
        params = (last_uid, BATCH_SIZE) if last_uid else (BATCH_SIZE,)
        cursor.execute(query_sql, params)
        rows = cursor.fetchall()
        if not rows: break

        all_chunks_text = []
        all_payloads = []

        for row in rows:
            cleaned_text = hybrid_clean(row['plaintext'] or "")
            if len(cleaned_text) < 20:
                last_uid = row['UID']
                continue

            chunks = chunker.split_text(cleaned_text)
            for i, chunk_text in enumerate(chunks):
                safe_text = chunk_text[:2000]
                all_chunks_text.append(safe_text)
                all_payloads.append({
                    "original_uid": row['UID'],
                    "subject": row['subject'],
                    "body": safe_text,
                    "email_date": str(row['email_date']),
                    "operators": [row['operator']] if row['operator'] else [],
                    "countries": [row['country']] if row['country'] else [],
                    "subs": [row['sub']] if row['sub'] else []
                })
            last_uid = row['UID']

        if all_chunks_text:
            dense_vectors = model.encode(all_chunks_text, batch_size=32, show_progress_bar=False)
            points = []

            for idx, (dense_vec, payload) in enumerate(zip(dense_vectors, all_payloads)):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{payload['original_uid']}_{idx}"))

                # Setup the hybrid vector point
                points.append(PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vec.tolist(),
                        "sparse": models.Document(text=payload['body'], model="Qdrant/bm25")
                    },
                    payload=payload
                ))

            q_client.upsert(collection_name=COLLECTION_NAME, points=points)

        with open(checkpoint_file, "w") as f:
            f.write(str(last_uid))
        pbar.update(len(rows))

    db.close()
    logging.info("✅ Hybrid Migration complete.")


if __name__ == "__main__":
    migrate()
