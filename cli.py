# C:\AI Projects\rag2\cli.py
# RAG2 with DGraph Knowledge Graph Enhancement
# Updated: enforce embedding model consistency (mpnet-768), Reranker (ms-marco-MiniLM-L6-v2) + Hybrid search & bug fixes

import os
import logging
import requests
import config
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from operator_data import get_query_context
from reranker import DocumentReranker
from integrate_dgraph import DGraphEnhancedRAG

# 🛡️ OFFLINE SAFETY
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logging.basicConfig(level=logging.ERROR)


class RagEngine:
    def __init__(self):
        self.q_client = QdrantClient(url=config.QDRANT_URL)
        print(f"📦 Loading Scout: {config.MODEL_PATH}")
        self.model = SentenceTransformer(config.MODEL_PATH, device="cpu")
        self.reranker = DocumentReranker()
        self.collection = config.COLLECTION_NAME
        self.base_threshold = getattr(config, "SCORE_THRESHOLD", 0.40)

        try:
            self.dgraph_rag = DGraphEnhancedRAG()
            self.dgraph_enabled = True
        except Exception:
            self.dgraph_enabled = False

    def _execute_hybrid_query(self, query_text, query_vector, q_filter=None, limit=None):
        """Unified helper to ensure we always use named vectors."""
        search_limit = limit or config.SEARCH_TOP_K
        return self.q_client.query_points(
            collection_name=self.collection,
            prefetch=[
                models.Prefetch(query=query_vector, using="dense", filter=q_filter, limit=search_limit),
                models.Prefetch(query=models.Document(text=query_text, model="Qdrant/bm25"), using="sparse",
                                filter=q_filter, limit=search_limit),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            with_payload=True
        ).points

    def search(self, query: str):
        # A. Knowledge Graph & Metadata
        expanded_ops = []
        if self.dgraph_enabled:
            try:
                enhancement = self.dgraph_rag.enhance_query(query)
                expanded_ops = enhancement.get("expanded_operators", [])
            except Exception:
                pass

        q_filter, label, _ = get_query_context(query, self.base_threshold, expanded_ops)
        query_vector = self.model.encode(query).tolist()

        # B. Stage 1: Filtered Hybrid Search
        print(f"🔍 Executing Filtered Hybrid Search [{label}]...")
        try:
            initial_hits = self._execute_hybrid_query(query, query_vector, q_filter)
        except Exception as e:
            print(f"⚠️ Hybrid failed: {e}. Falling back to Dense.")
            initial_hits = self.q_client.query_points(
                collection_name=self.collection,
                query={"dense": query_vector},  # Fixed: Use named vector here too
                query_filter=q_filter,
                limit=config.SEARCH_TOP_K
            ).points

        # C. Stage 2: Initial Reranking
        final_hits = []
        top_score = -10.0
        if initial_hits:
            final_hits = self.reranker.rerank(query, initial_hits)
            top_score = final_hits[0].score if final_hits else -10.0

        # 🔄 RERANK-DRIVEN FALLBACK
        # Trigger if score is low (< 0.5) or no hits found
        if not final_hits or top_score < 0.5:
            print(f"🟡 Low confidence ({top_score:.2f}). Triggering Broad Search (No Filters)...")
            broad_hits = self._execute_hybrid_query(query, query_vector, q_filter=None, limit=20)

            if broad_hits:
                fallback_results = self.reranker.rerank(query, broad_hits)
                fallback_score = fallback_results[0].score if fallback_results else -10.0

                # Only adopt fallback if it's significantly better
                if fallback_score > top_score:
                    final_hits = fallback_results
                    top_score = fallback_score
                    label = f"Broad Search (High Confidence)"

        return final_hits, label, top_score

def call_agent(agent_cfg, context, query):
    prompt = f"### ROLE: {agent_cfg['name']}\n### TASK: {agent_cfg['focus']}\n### DATA:\n{context}\n\nQUERY: {query}"
    payload = {"input_type": "chat", "output_type": "chat", "input_value": prompt}
    headers = {"x-api-key": config.AGENT_API_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(config.AGENT_API_URL, json=payload, headers=headers, timeout=90)
        data = r.json()
        # Resilient extraction
        try:
            return data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        except (KeyError, IndexError):
            return data.get("result", data.get("response", "⚠️ Error: Unknown API format"))
    except Exception as e:
        return f"⚠️ Agent Error: {str(e)}"


def run_cli():
    engine = RagEngine()
    print(f"\n🚀 RAG2 CORE | HYBRID + RERANK FALLBACK ACTIVE")

    while True:
        query = input("\n🔍 Query: ").strip()
        if query.lower() in ["exit", "quit"]: break
        if not query: continue

        hits, label, top_score = engine.search(query)
        if not hits:
            print(f"❌ No matching data found.")
            continue

        # D. Safe Chronological Context (Top 5)
        # Sort by date before sending to agent
        hits_to_process = sorted(hits[:5], key=lambda x: x.payload.get('email_date', ''), reverse=False)

        context_str = ""
        unique_ops = set()
        for h in hits_to_process:
            p = h.payload
            ops = p.get("operators", ["Uncategorized"])
            op_name = ops[0] if ops else "Uncategorized"
            unique_ops.add(op_name)

            dt = p.get("email_date", "N/A")
            subj = p.get("subject", "No Subject")
            body = (p.get("body") or "No content")[:config.BODY_TRUNCATE].replace("\n", " ")
            context_str += f"[Date: {dt} | Op: {op_name}] Subj: {subj} | Body: {body}\n---\n"

        status_icon = "🟢" if top_score > 3.0 else "🟡" if top_score > 0 else "🟠"
        print(f"\n✅ Scope: {label} ({', '.join(unique_ops)})")
        print(f"{status_icon} Rerank Score: {top_score:.2f}")
        print("-" * 60)

        for agent in config.AGENTS:
            print(f"\n🤖 {agent['name'].upper()}:")
            print(call_agent(agent, context_str, query))


if __name__ == "__main__":
    run_cli()
