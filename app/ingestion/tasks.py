"""Background tasks for indexing knowledge sources."""

import threading
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from rich.console import Console

from app.models import get_db, KnowledgeSource, MonitoredChannel, SourceType, SourceStatus
from app.ingestion.crawler import DocsCrawler
from app.ingestion.github import GitHubFetcher, GitHubIssuesFetcher
from app.ingestion.slack_history import SlackHistoryFetcher
from app.ingestion.chunker import TextChunker
from app.ingestion.embedder import Embedder
from app.retrieval.vector_store import VectorStore

console = Console()


def trigger_indexing(channel_id: str):
    """Trigger indexing for all pending sources in a channel."""
    thread = threading.Thread(target=_index_channel_sources, args=(channel_id,))
    thread.daemon = True
    thread.start()


def _notify_slack(slack_channel_id: str, message: str):
    """Send a notification to Slack channel."""
    try:
        from app.config import settings
        from slack_sdk import WebClient
        client = WebClient(token=settings.slack_bot_token)
        client.chat_postMessage(channel=slack_channel_id, text=message)
    except Exception as e:
        console.print(f"[yellow]Failed to notify Slack:[/yellow] {e}")


def _index_channel_sources(channel_id: str):
    """Index all pending sources for a channel."""
    db = next(get_db())
    vector_store = VectorStore(channel_id)
    chunker = TextChunker()
    embedder = Embedder()
    
    # Get channel info for Slack notification
    channel = db.query(MonitoredChannel).filter_by(id=channel_id).first()
    slack_channel_id = channel.slack_channel_id if channel else None
    
    sources = db.query(KnowledgeSource).filter_by(
        channel_id=channel_id,
        status=SourceStatus.PENDING
    ).all()
    
    console.print(f"[blue]Indexing {len(sources)} sources for channel {channel_id[:8]}...[/blue]")
    
    for source in sources:
        try:
            source.status = SourceStatus.INDEXING
            db.commit()
            
            chunks = []
            
            if source.source_type == SourceType.DOCUMENTATION:
                chunks = _index_documentation(source.url, chunker)
            elif source.source_type in [SourceType.GITHUB_OPERATOR, SourceType.GITHUB_OPERAND]:
                chunks = _index_github(source.url, source.source_type.value, chunker)
            elif source.source_type == SourceType.GITHUB_ISSUES:
                chunks = _index_github_issues(source.url, chunker)
            elif source.source_type == SourceType.SLACK_HISTORY:
                chunks = _index_slack_history(source.url, chunker)
            
            if chunks:
                # Generate embeddings and store
                texts = [c["content"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]
                embeddings = embedder.embed(texts)
                
                vector_store.add(texts, embeddings, metadatas)
                console.print(f"  [green]✓ Indexed {len(chunks)} chunks from {source.source_type.value}[/green]")
            
            source.status = SourceStatus.INDEXED
            source.last_indexed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            db.rollback()  # Rollback failed transaction
            console.print(f"  [red]✗ Failed to index source:[/red] {e}")
            try:
                # Refresh the source object and update status
                db.refresh(source)
                source.status = SourceStatus.FAILED
                source.error_message = str(e)[:500]
                db.commit()
            except Exception:
                db.rollback()  # Give up if this also fails
    
    console.print(f"[green]✓ Indexing complete for channel {channel_id[:8]}[/green]")
    
    # Notify Slack that indexing is complete
    if slack_channel_id:
        indexed = db.query(KnowledgeSource).filter_by(channel_id=channel_id, status=SourceStatus.INDEXED).count()
        failed = db.query(KnowledgeSource).filter_by(channel_id=channel_id, status=SourceStatus.FAILED).count()
        
        if failed == 0:
            _notify_slack(slack_channel_id, f"✅ Ready! Indexed {indexed} knowledge source(s). Ask me anything!")
        else:
            _notify_slack(slack_channel_id, f"⚠️ Indexing done. {indexed} succeeded, {failed} failed. I'll do my best with what I have!")


def _index_documentation(url: str, chunker: TextChunker) -> list[dict]:
    """Index a documentation site."""
    crawler = DocsCrawler(url, max_pages=500, max_depth=5)
    chunks = []
    
    for page in crawler.crawl():
        for chunk in chunker.chunk_text(page.content, {
            "source_type": "documentation",
            "url": page.url,
            "title": page.title
        }):
            chunks.append({
                "content": chunk.content,
                "metadata": chunk.metadata
            })
    
    return chunks


def _index_github(url: str, source_type: str, chunker: TextChunker) -> list[dict]:
    """Index a GitHub repository."""
    fetcher = GitHubFetcher(url, max_files=100)
    chunks = []
    
    for file in fetcher.fetch():
        for chunk in chunker.chunk_text(file.content, {
            "source_type": source_type,
            "url": file.url,
            "file_path": file.path,
            "file_type": file.file_type
        }):
            chunks.append({
                "content": chunk.content,
                "metadata": chunk.metadata
            })
    
    return chunks


def _index_github_issues(url: str, chunker: TextChunker) -> list[dict]:
    """Index GitHub issues (both open and closed)."""
    fetcher = GitHubIssuesFetcher(url, max_issues=100, include_closed=True)
    chunks = []
    
    for issue in fetcher.fetch():
        # Combine issue title, body, and comments into one document
        content_parts = [
            f"# Issue #{issue.number}: {issue.title}",
            f"Status: {issue.state}",
            f"Labels: {', '.join(issue.labels) if issue.labels else 'none'}",
            "",
            issue.body,
        ]
        
        if issue.comments:
            content_parts.append("\n## Comments:")
            for i, comment in enumerate(issue.comments, 1):
                content_parts.append(f"\n### Comment {i}:\n{comment}")
        
        content = "\n".join(content_parts)
        
        for chunk in chunker.chunk_text(content, {
            "source_type": "github_issues",
            "url": issue.url,
            "issue_number": issue.number,
            "issue_state": issue.state,
            "labels": issue.labels
        }):
            chunks.append({
                "content": chunk.content,
                "metadata": chunk.metadata
            })
    
    return chunks


def _index_slack_history(url: str, chunker: TextChunker) -> list[dict]:
    """Index Slack conversation history."""
    # Parse URL: slack://CHANNEL_ID?days=30
    parsed = urlparse(url)
    channel_id = parsed.netloc
    days = int(parse_qs(parsed.query).get("days", [30])[0])
    
    fetcher = SlackHistoryFetcher(channel_id, days)
    chunks = []
    
    # Group messages into conversations for better context
    current_conversation = []
    last_thread = None
    
    for message in fetcher.fetch():
        # Group by thread or time proximity
        if message.thread_ts != last_thread and current_conversation:
            # Flush current conversation
            text = "\n".join(m.text for m in current_conversation)
            for chunk in chunker.chunk_text(text, {
                "source_type": "slack_history",
                "url": current_conversation[0].url
            }):
                chunks.append({
                    "content": chunk.content,
                    "metadata": chunk.metadata
                })
            current_conversation = []
        
        current_conversation.append(message)
        last_thread = message.thread_ts
    
    # Flush remaining
    if current_conversation:
        text = "\n".join(m.text for m in current_conversation)
        for chunk in chunker.chunk_text(text, {
            "source_type": "slack_history",
            "url": current_conversation[0].url
        }):
            chunks.append({
                "content": chunk.content,
                "metadata": chunk.metadata
            })
    
    return chunks


