"""Slack conversation history fetcher."""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Generator
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from rich.console import Console

from app.config import settings

console = Console()


@dataclass
class SlackMessage:
    """A message from Slack history."""
    text: str
    user: str
    timestamp: str
    thread_ts: str | None
    url: str


class SlackHistoryFetcher:
    """Fetch conversation history from Slack channels."""
    
    def __init__(self, channel_id: str, days: int = 30):
        self.channel_id = channel_id
        self.days = days
        self.client = WebClient(token=settings.slack_bot_token)
    
    def fetch(self) -> Generator[SlackMessage, None, None]:
        """Fetch messages from the channel."""
        console.print(f"[blue]Fetching Slack history:[/blue] {self.days} days")
        
        oldest = (datetime.now() - timedelta(days=self.days)).timestamp()
        message_count = 0
        
        try:
            # Get channel info for URL construction
            channel_info = self.client.conversations_info(channel=self.channel_id)
            team_id = channel_info.get("channel", {}).get("context_team_id", "")
            
            cursor = None
            while True:
                response = self.client.conversations_history(
                    channel=self.channel_id,
                    oldest=str(oldest),
                    limit=200,
                    cursor=cursor
                )
                
                for message in response.get("messages", []):
                    # Skip bot messages and system messages
                    if message.get("subtype"):
                        continue
                    
                    text = message.get("text", "").strip()
                    if not text or len(text) < 10:
                        continue
                    
                    user = message.get("user", "unknown")
                    ts = message.get("ts", "")
                    thread_ts = message.get("thread_ts")
                    
                    # Construct message URL
                    url = f"https://slack.com/archives/{self.channel_id}/p{ts.replace('.', '')}"
                    
                    message_count += 1
                    yield SlackMessage(
                        text=text,
                        user=user,
                        timestamp=ts,
                        thread_ts=thread_ts,
                        url=url
                    )
                    
                    # Also fetch thread replies if this is a thread parent
                    if thread_ts is None and message.get("reply_count", 0) > 0:
                        yield from self._fetch_thread(ts)
                
                # Check for more pages
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            console.print(f"[green]Slack history fetched:[/green] {message_count} messages")
            
        except SlackApiError as e:
            console.print(f"[red]Slack API error:[/red] {e}")
    
    def _fetch_thread(self, thread_ts: str) -> Generator[SlackMessage, None, None]:
        """Fetch replies in a thread."""
        try:
            response = self.client.conversations_replies(
                channel=self.channel_id,
                ts=thread_ts,
                limit=100
            )
            
            # Skip the first message (parent) as it's already yielded
            for message in response.get("messages", [])[1:]:
                if message.get("subtype"):
                    continue
                
                text = message.get("text", "").strip()
                if not text or len(text) < 10:
                    continue
                
                user = message.get("user", "unknown")
                ts = message.get("ts", "")
                
                url = f"https://slack.com/archives/{self.channel_id}/p{ts.replace('.', '')}"
                
                yield SlackMessage(
                    text=text,
                    user=user,
                    timestamp=ts,
                    thread_ts=thread_ts,
                    url=url
                )
                
        except SlackApiError as e:
            console.print(f"  [red]Error fetching thread:[/red] {e}")


