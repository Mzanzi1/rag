# rag2/chunking.py
from typing import List
from transformers import AutoTokenizer


class TokenAwareChunker:
    def __init__(self, model_name: str, chunk_size: int = 450, chunk_overlap: int = 50):
        """
        model_name: The path or HF name (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
        chunk_size: Target tokens per chunk (keeping under the 512 limit)
        chunk_overlap: Number of tokens to repeat between chunks
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Splits text into token-limited chunks while trying to preserve sentence boundaries.
        """
        if not text:
            return []

        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        chunks = []

        start = 0
        while start < len(tokens):
            # Define the end of the current chunk
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]

            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens, clean_up_tokenization_spaces=True)
            chunks.append(chunk_text)

            # Move the pointer, accounting for overlap
            if end == len(tokens):
                break
            start = end - self.chunk_overlap

        return chunks

# Example usage in your SQL script:
# chunker = TokenAwareChunker(MODEL_PATH)
# chunks = chunker.split_text(email_body)
