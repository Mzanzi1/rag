from qdrant_client import QdrantClient, models

client = QdrantClient("http://localhost:6333")
COLLECTION_NAME = "email_records"

# 1. Check if collection exists before creating
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=768,  # MPNet dimension
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        }
    )
    print(f"✅ Collection '{COLLECTION_NAME}' created with Hybrid support.")
else:
    print(f"ℹ️ Collection '{COLLECTION_NAME}' already exists. Skipping creation.")
