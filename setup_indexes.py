# rag2/setup_indexes.py
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from config import QDRANT_URL, COLLECTION_NAME

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def initialize_qdrant():
    client = QdrantClient(url=QDRANT_URL)

    # 1. Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)

    if not exists:
        logging.info(f"Creating collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384,  # all-MiniLM-L6-v2 dimension
                distance=models.Distance.COSINE
            )
        )
    else:
        logging.info(f"Collection {COLLECTION_NAME} already exists.")

    # 2. Create Payload Indexes (The "Pre-Filter" Magic)
    # Keyword indexes are best for categories like Operators/Countries
    fields_to_index = {
        "operators": models.PayloadSchemaType.KEYWORD,
        "countries": models.PayloadSchemaType.KEYWORD,
        "subs": models.PayloadSchemaType.KEYWORD,
        "email_date": models.PayloadSchemaType.DATETIME
    }

    for field_name, schema_type in fields_to_index.items():
        try:
            logging.info(f"Ensuring index on field: {field_name} ({schema_type})")
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=schema_type
            )
        except Exception as e:
            logging.warning(f"Note for {field_name}: {e}")

    logging.info("✅ Qdrant Performance Indexing Complete.")


if __name__ == "__main__":
    initialize_qdrant()
