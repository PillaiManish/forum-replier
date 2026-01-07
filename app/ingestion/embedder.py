"""Embedding generation using sentence transformers."""

from sentence_transformers import SentenceTransformer
from rich.console import Console

console = Console()

# Global model instance (loaded once)
_model = None


def get_model() -> SentenceTransformer:
    """Get or create the embedding model."""
    global _model
    if _model is None:
        console.print("[blue]Loading embedding model...[/blue]")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        console.print("[green]✓ Embedding model loaded[/green]")
    return _model


class Embedder:
    """Generate embeddings for text chunks."""
    
    def __init__(self):
        self.model = get_model()
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
        embedding = self.model.encode([query], show_progress_bar=False)
        return embedding[0].tolist()


