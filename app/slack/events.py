"""Slack event handlers for messages and reactions."""

from slack_bolt import App
from slack_sdk import WebClient
from rich.console import Console

from app.slack.bot import app
from app.models import get_db, MonitoredChannel, ConversationLog
from app.query.pipeline import answer_question

console = Console()


@app.event("app_home_opened")
def handle_app_home(client: WebClient, event: dict):
    """Display app home tab with welcome message."""
    user_id = event["user"]
    
    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "👋 Welcome to Forum Replier!"}
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "I help answer questions in your forums by referencing:\n"
                            "• 📚 Documentation sites\n"
                            "• 🐙 GitHub repositories\n"
                            "• 💬 Channel conversation history\n\n"
                            "*To get started:*\n"
                            "1. Invite me to a channel: `/invite @Forum Replier`\n"
                            "2. Mention me with `configure` to set up knowledge sources\n"
                            "3. Ask questions and I'll help answer them!"
                        )
                    }
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "💡 Tip: React with 👍 or 👎 to help me learn!"}
                    ]
                }
            ]
        }
    )


@app.event("message")
def handle_message(client: WebClient, event: dict, say):
    """Handle incoming messages."""
    # Ignore bot messages and message edits
    if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        return
    
    # Ignore messages without text
    text = event.get("text", "").strip()
    if not text:
        return
    
    channel_id = event.get("channel")
    user_id = event.get("user")
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    # Get bot user ID
    bot_info = client.auth_test()
    bot_user_id = bot_info["user_id"]
    
    # Check if bot was mentioned
    bot_mentioned = f"<@{bot_user_id}>" in text
    
    if not bot_mentioned:
        return
    
    # Remove bot mention from text
    clean_text = text.replace(f"<@{bot_user_id}>", "").strip()
    
    # Handle configure command - send button (messages don't have trigger_id)
    if clean_text.lower() in ["configure", "config", "setup"]:
        client.chat_postMessage(
            channel=channel_id,
            text="Click to configure my knowledge sources:",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Click the button below to configure my knowledge sources:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "⚙️ Configure"},
                            "style": "primary",
                            "action_id": "open_config_modal",
                            "value": channel_id
                        }
                    ]
                }
            ]
        )
        return
    
    # Check if channel is configured
    db = next(get_db())
    channel = db.query(MonitoredChannel).filter_by(slack_channel_id=channel_id).first()
    
    if not channel:
        say(
            text=(
                "Hi! I'm not configured for this channel yet.\n"
                "Mention me with `configure` to set up my knowledge sources!"
            ),
            thread_ts=thread_ts
        )
        return
    
    # Answer the question
    console.print(f"[blue]Question from {user_id}:[/blue] {clean_text[:100]}...")
    
    try:
        result = answer_question(clean_text, channel.id, db)
        
        # Log the conversation
        log = ConversationLog(
            channel_id=channel.id,
            thread_ts=thread_ts,
            user_id=user_id,
            question=clean_text,
            answer=result["answer"],
            sources_used=result.get("sources"),
            confidence=result.get("confidence", "medium")
        )
        db.add(log)
        db.commit()
        
        # Format response with sources
        response = result["answer"]
        if result.get("sources"):
            sources_text = "\n".join(f"• {s}" for s in result["sources"][:3])
            response += f"\n\n_Sources:_\n{sources_text}"
        
        # Reply in thread
        say(text=response, thread_ts=thread_ts)
        
    except Exception as e:
        console.print(f"[red]Error answering question:[/red] {e}")
        say(
            text=f"😅 Sorry, I couldn't find a good answer. Something went wrong: {str(e)[:100]}\n\nA human should take a look at this!",
            thread_ts=thread_ts
        )


@app.event("reaction_added")
def handle_reaction(client: WebClient, event: dict):
    """Track feedback from reactions."""
    reaction = event.get("reaction", "")
    
    # Only track thumbs up/down
    if reaction not in ["+1", "-1", "thumbsup", "thumbsdown"]:
        return
    
    item = event.get("item", {})
    if item.get("type") != "message":
        return
    
    channel_id = item.get("channel")
    message_ts = item.get("ts")
    
    # Find the conversation log for this message
    db = next(get_db())
    channel = db.query(MonitoredChannel).filter_by(slack_channel_id=channel_id).first()
    
    if not channel:
        return
    
    # Update feedback
    log = db.query(ConversationLog).filter_by(
        channel_id=channel.id,
        thread_ts=message_ts
    ).first()
    
    if log:
        log.feedback = "thumbsup" if reaction in ["+1", "thumbsup"] else "thumbsdown"
        db.commit()
        console.print(f"[yellow]Feedback recorded:[/yellow] {log.feedback} for {log.id[:8]}")


@app.event("app_mention")
def handle_app_mention(client: WebClient, event: dict, say):
    """Handle direct @mentions - delegates to message handler."""
    # The message event handler already handles mentions
    pass


@app.event("member_joined_channel")
def handle_member_joined(client: WebClient, event: dict):
    """Handle bot joining a channel - offer config if not configured."""
    # Check if it's the bot that joined
    bot_info = client.auth_test()
    if event.get("user") != bot_info["user_id"]:
        return  # Not the bot, ignore
    
    channel_id = event.get("channel")
    
    # Check if channel is already configured
    db = next(get_db())
    channel = db.query(MonitoredChannel).filter_by(slack_channel_id=channel_id).first()
    
    if channel:
        return  # Already configured, no action needed
    
    # Not configured - show config button
    client.chat_postMessage(
        channel=channel_id,
        text="I need to be configured before I can help answer questions.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "👋 I need to be configured before I can help answer questions in this channel."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⚙️ Configure"},
                        "style": "primary",
                        "action_id": "open_config_modal",
                        "value": channel_id
                    }
                ]
            }
        ]
    )


