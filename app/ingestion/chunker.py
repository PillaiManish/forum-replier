"""Text chunking for embedding and retrieval."""

from dataclasses import dataclass
from typing import Generator


@dataclass
class Chunk:
    """A chunk of text for embedding."""
    content: str
    metadata: dict


class TextChunker:
    """Split text into overlapping chunks for better retrieval."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: dict = None) -> Generator[Chunk, None, None]:
        """Split text into overlapping chunks."""
        metadata = metadata or {}
        
        # Clean text
        text = text.strip()
        if not text:
            return
        
        # Split by paragraphs first to maintain semantic boundaries
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                # Yield current chunk if it has content
                if current_chunk.strip():
                    yield Chunk(content=current_chunk.strip(), metadata=metadata.copy())
                
                # If paragraph itself is larger than chunk size, split it
                if len(paragraph) > self.chunk_size:
                    yield from self._split_large_text(paragraph, metadata)
                    current_chunk = ""
                else:
                    # Start new chunk with overlap from previous
                    overlap = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = overlap + "\n\n" + paragraph if overlap else paragraph
            else:
                # Add paragraph to current chunk
                current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
        
        # Yield remaining content
        if current_chunk.strip():
            yield Chunk(content=current_chunk.strip(), metadata=metadata.copy())
    
    def _split_large_text(self, text: str, metadata: dict) -> Generator[Chunk, None, None]:
        """Split large text by sentences or fixed size."""
        # Try to split by sentences
        sentences = text.replace(". ", ".\n").split("\n")
        
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk.strip():
                    yield Chunk(content=current_chunk.strip(), metadata=metadata.copy())
                current_chunk = sentence
            else:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            yield Chunk(content=current_chunk.strip(), metadata=metadata.copy())


