"""Vector store using ChromaDB for similarity search."""

import os
import chromadb
from chromadb.config import Settings
from rich.console import Console

from app.config import settings

console = Console()

# Disable telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "false"


class VectorStore:
    """ChromaDB-based vector store for document chunks."""
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.collection_name = f"channel_{channel_id.replace('-', '_')}"
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add(self, texts: list[str], embeddings: list[list[float]], metadatas: list[dict]):
        """Add documents to the vector store."""
        if not texts:
            return
        
        # Generate unique IDs
        import uuid
        ids = [str(uuid.uuid4()) for _ in texts]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
    
    def query(self, query_embedding: list[float], n_results: int = 5) -> list[dict]:
        """Query the vector store for similar documents."""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            return [
                {
                    "content": doc,
                    "metadata": meta,
                    "score": 1 - dist  # Convert distance to similarity score
                }
                for doc, meta, dist in zip(documents, metadatas, distances)
            ]
            
        except Exception as e:
            console.print(f"[red]Vector store query error:[/red] {e}")
            return []
    
    def count(self) -> int:
        """Get the number of documents in the collection."""
        return self.collection.count()
    
    def clear(self):
        """Clear all documents from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )


