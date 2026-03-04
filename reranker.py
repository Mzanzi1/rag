# C:\AI Projects\rag2\reranker.py
# Cross-encoder reranker for improved relevance scoring
# Corporate firewall safe with offline mode and graceful degradation

import os
import config
from sentence_transformers import CrossEncoder

# 🛡️ Force Offline Mode: Essential for Corporate Firewalls
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


class DocumentReranker:
    """
    Uses a cross-encoder to rerank search results for better relevance.

    Cross-encoders are slower but more accurate than bi-encoders because
    they jointly encode the query and document together.

    Features:
    - Offline mode (no internet required)
    - Graceful degradation (system works even if reranker fails)
    - Handles multiple payload formats
    - Configurable top-k results
    """

    def __init__(self, model_path=None):
        """
        Initialize the reranker with offline support.

        Args:
            model_path: Path to local cross-encoder model.
                       If None, uses config.RERANKER_PATH
        """
        # Use provided path or fall back to config
        if model_path is None:
            model_path = getattr(config, 'RERANKER_PATH', None)

        if not model_path:
            print("⚠️  No RERANKER_PATH in config. Reranker disabled.")
            self.model = None
            return

        # Normalize path for Windows
        clean_path = os.path.normpath(model_path)

        # Verify model files exist
        weights_file = os.path.join(clean_path, "pytorch_model.bin")
        config_file = os.path.join(clean_path, "config.json")

        if not os.path.exists(clean_path):
            print(f"⚠️  Reranker directory NOT FOUND: {clean_path}")
            print("   System will continue without reranking.")
            self.model = None
            return

        if not os.path.exists(weights_file):
            print(f"⚠️  Reranker weights NOT FOUND: {weights_file}")
            print("   Expected files:")
            print("      - pytorch_model.bin (or model.safetensors)")
            print("      - config.json")
            print("      - tokenizer.json")
            print("   System will continue without reranking.")
            self.model = None
            return

        if not os.path.exists(config_file):
            print(f"⚠️  Reranker config NOT FOUND: {config_file}")
            print("   System will continue without reranking.")
            self.model = None
            return

        # Load the model
        try:
            # local_files_only=True prevents 'WinError 10060' timeout errors
            self.model = CrossEncoder(
                clean_path,
                device='cpu',
                local_files_only=True
            )
            print(f"✅ Offline Reranker loaded: {clean_path}")

        except Exception as e:
            print(f"❌ Error loading Reranker: {e}")
            print("   System will continue without reranking.")
            self.model = None

    def is_enabled(self) -> bool:
        """Check if reranker is available."""
        return self.model is not None

    def rerank(self, query: str, hits: list, top_k: int = None):
        """
        Rerank search results using cross-encoder.

        The cross-encoder performs deep comparison between the query
        and each document, giving more accurate relevance scores than
        the initial bi-encoder search.

        Args:
            query: User query string
            hits: List of Qdrant points from initial search
            top_k: Number of results to return (defaults to config.RERANK_TOP_K)

        Returns:
            Reranked list of hits with updated scores
        """
        # Get top_k from config if not provided
        if top_k is None:
            top_k = getattr(config, 'RERANK_TOP_K', 10)

        # If reranker not available or no hits, return original results
        if not self.model or not hits:
            return hits[:top_k]

        try:
            # Prepare query-document pairs
            sentence_pairs = []

            for hit in hits:
                # Extract document text from payload
                # Try multiple field names for flexibility
                body = (
                        hit.payload.get("body") or
                        hit.payload.get("content") or
                        hit.payload.get("text") or
                        ""
                )

                # Optionally include subject for better context
                subject = hit.payload.get("subject", "")

                # Combine subject and body (cross-encoder can handle longer text)
                if subject:
                    full_text = f"{subject} {body}"
                else:
                    full_text = body

                # Create query-document pair
                sentence_pairs.append([query, str(full_text)])

            # Get reranking scores from cross-encoder
            # This is the slow but accurate step
            scores = self.model.predict(sentence_pairs)

            # Update hit scores with reranking scores
            for i, hit in enumerate(hits):
                hit.score = float(scores[i])

            # Sort by new scores (highest first)
            reranked = sorted(hits, key=lambda x: x.score, reverse=True)

            # Return top-k results
            return reranked[:top_k]

        except Exception as e:
            print(f"⚠️  Reranking failed: {e}")
            print("   Returning original results without reranking.")
            return hits[:top_k]

    def rerank_with_explanations(self, query: str, hits: list, top_k: int = None):
        """
        Rerank and provide score explanations (for debugging).

        Args:
            query: User query string
            hits: List of Qdrant points
            top_k: Number of results to return

        Returns:
            Tuple of (reranked_hits, explanations)
        """
        if top_k is None:
            top_k = getattr(config, 'RERANK_TOP_K', 10)

        if not self.model or not hits:
            return hits[:top_k], ["Reranker not available"]

        # Store original scores
        original_scores = [hit.score for hit in hits]

        # Rerank
        reranked = self.rerank(query, hits, top_k)

        # Generate explanations
        explanations = []
        for i, hit in enumerate(reranked):
            original_idx = hits.index(hit)
            original_score = original_scores[original_idx]
            new_score = hit.score

            change = "↑ improved" if new_score > original_score else "↓ decreased" if new_score < original_score else "→ same"

            explanations.append(
                f"Rank {i + 1}: Original score: {original_score:.3f}, "
                f"Rerank score: {new_score:.3f} ({change})"
            )

        return reranked, explanations


# ============================================================================
# Helper Functions for Testing
# ============================================================================
def test_reranker():
    """Quick test to verify reranker is working."""
    print("=" * 80)
    print("RERANKER TEST")
    print("=" * 80)

    reranker = DocumentReranker()

    if not reranker.is_enabled():
        print("❌ Reranker is not enabled")
        print("   Check:")
        print("   1. config.RERANKER_PATH is set correctly")
        print("   2. Model files exist in that directory")
        print("   3. Model files are not corrupted")
        return False

    print("✅ Reranker is enabled and ready")
    return True


if __name__ == "__main__":
    # Run test when module is executed directly
    test_reranker()
