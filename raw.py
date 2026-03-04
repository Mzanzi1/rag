#raw
from qdrant_client import QdrantClient
from config import QDRANT_URL, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL)

# Scroll a few points to see if any exist
scroll_resp = client.scroll(collection_name=COLLECTION_NAME, limit=5)
if isinstance(scroll_resp, tuple):
    scroll_resp = scroll_resp[0]

points = scroll_resp.points if hasattr(scroll_resp, 'points') else scroll_resp
print(f"✅ Number of points retrieved: {len(points)}")
if points:
    for idx, p in enumerate(points, 1):
        payload = getattr(p, 'payload', {}) if hasattr(p, 'payload') else p
        print(f"{idx}. Subject: {payload.get('subject', 'No Subject')}")
        print(f"   Date: {payload.get('email_date', 'Unknown date')}")
        print(f"   Body (first 100 chars): {payload.get('body', '')[:100]}\n")
