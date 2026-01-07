"""Slack bot initialization and startup."""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from rich.console import Console

from app.config import settings
from app.models import init_db

console = Console()

# Initialize Slack app
app = App(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)


def create_app() -> App:
    """Create and configure the Slack app."""
    # Import handlers to register them
    from app.slack import events  # noqa: F401
    from app.slack import modals  # noqa: F401
    
    return app


def start_bot():
    """Start the bot in socket mode."""
    console.print("[bold green]🚀 Starting Forum Replier Bot...[/bold green]")
    
    # Initialize database
    init_db()
    console.print("[green]✓[/green] Database initialized")
    
    # Create app with handlers
    create_app()
    console.print("[green]✓[/green] Slack handlers registered")
    
    # Start socket mode
    handler = SocketModeHandler(app, settings.slack_app_token)
    console.print("[bold green]✓ Bot is running! Press Ctrl+C to stop.[/bold green]")
    handler.start()


