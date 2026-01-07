"""Query pipeline for answering questions."""

from sqlalchemy.orm import Session
from rich.console import Console

from app.retrieval.vector_store import VectorStore
from app.ingestion.embedder import Embedder
from app.query.llm import generate_answer

console = Console()


def answer_question(question: str, channel_id: str, db: Session) -> dict:
    """
    Answer a question using RAG pipeline.
    
    Returns:
        dict with keys: answer, sources, confidence
    """
    # Initialize components
    vector_store = VectorStore(channel_id)
    embedder = Embedder()
    
    # Check if we have any indexed content
    doc_count = vector_store.count()
    if doc_count == 0:
        return {
            "answer": "I don't have any knowledge indexed yet. Please configure my knowledge sources first!",
            "sources": [],
            "confidence": "low"
        }
    
    console.print(f"[blue]Searching {doc_count} chunks for:[/blue] {question[:50]}...")
    
    # Generate query embedding
    query_embedding = embedder.embed_query(question)
    
    # Retrieve relevant chunks
    results = vector_store.query(query_embedding, n_results=5)
    
    if not results:
        return {
            "answer": "I couldn't find relevant information to answer your question.",
            "sources": [],
            "confidence": "low"
        }
    
    # Build context from retrieved chunks
    context_parts = []
    sources = []
    
    for result in results:
        content = result["content"]
        metadata = result.get("metadata", {})
        score = result.get("score", 0)
        
        # Only include reasonably relevant chunks
        if score < 0.3:
            continue
        
        context_parts.append(content)
        
        # Track sources
        source = metadata.get("url") or metadata.get("file_path")
        if source and source not in sources:
            sources.append(source)
    
    if not context_parts:
        return {
            "answer": "I found some content but it doesn't seem relevant to your question. Could you rephrase?",
            "sources": [],
            "confidence": "low"
        }
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Generate answer using LLM
    console.print(f"[blue]Generating answer from {len(context_parts)} chunks...[/blue]")
    
    try:
        answer, confidence = generate_answer(question, context)
        
        return {
            "answer": answer,
            "sources": sources[:3],  # Top 3 sources
            "confidence": confidence
        }
        
    except Exception as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise RuntimeError(f"Failed to generate answer: {e}")


