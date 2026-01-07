"""Slack modals for bot configuration."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from rich.console import Console

from app.slack.bot import app
from app.models import get_db, Workspace, MonitoredChannel, KnowledgeSource, SourceType, SourceStatus
from app.ingestion.tasks import trigger_indexing

console = Console()


def open_config_modal(client: WebClient, trigger_id: str, channel_id: str):
    """Open the configuration modal for a channel."""
    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "config_modal",
                "private_metadata": channel_id,
                "title": {"type": "plain_text", "text": "Configure Forum Replier"},
                "submit": {"type": "plain_text", "text": "Save & Index"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Set up knowledge sources for this channel. I'll use these to answer questions."
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📚 Documentation"}
                    },
                    {
                        "type": "input",
                        "block_id": "docs_urls",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "docs_urls_input",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "https://docs.example.com/guide\nhttps://docs.example.com/api"
                            }
                        },
                        "label": {"type": "plain_text", "text": "Documentation URLs (one per line)"},
                        "hint": {"type": "plain_text", "text": "Each URL will be crawled with prefix-scoping (stays within that path)"}
                    },
                    {"type": "divider"},
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "🐙 GitHub Repositories"}
                    },
                    {
                        "type": "input",
                        "block_id": "github_operator",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "github_operator_input",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "https://github.com/org/operator-repo"
                            }
                        },
                        "label": {"type": "plain_text", "text": "Operator Repository URL"}
                    },
                    {
                        "type": "input",
                        "block_id": "github_operand",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "github_operand_input",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "https://github.com/org/operand-repo"
                            }
                        },
                        "label": {"type": "plain_text", "text": "Operand Repository URL (optional)"}
                    },
                    {
                        "type": "input",
                        "block_id": "github_issues",
                        "optional": True,
                        "element": {
                            "type": "checkboxes",
                            "action_id": "github_issues_checkbox",
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "Index GitHub Issues"},
                                    "description": {"type": "plain_text", "text": "Include open & closed issues from operator repo"},
                                    "value": "include_issues"
                                }
                            ]
                        },
                        "label": {"type": "plain_text", "text": "🎫 GitHub Issues"}
                    },
                    {"type": "divider"},
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "💬 Slack History"}
                    },
                    {
                        "type": "input",
                        "block_id": "slack_history_days",
                        "optional": True,
                        "element": {
                            "type": "static_select",
                            "action_id": "slack_history_select",
                            "placeholder": {"type": "plain_text", "text": "Select days"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "Last 7 days"}, "value": "7"},
                                {"text": {"type": "plain_text", "text": "Last 30 days"}, "value": "30"},
                                {"text": {"type": "plain_text", "text": "Last 90 days"}, "value": "90"},
                                {"text": {"type": "plain_text", "text": "Don't index"}, "value": "0"}
                            ],
                            "initial_option": {"text": {"type": "plain_text", "text": "Last 30 days"}, "value": "30"}
                        },
                        "label": {"type": "plain_text", "text": "Index conversation history"}
                    }
                ]
            }
        )
    except SlackApiError as e:
        console.print(f"[red]Error opening modal:[/red] {e}")


@app.action("docs_urls_input")
def handle_docs_input(ack):
    """Acknowledge docs input action."""
    ack()


@app.action("github_operator_input")
def handle_github_operator_input(ack):
    """Acknowledge GitHub operator input action."""
    ack()


@app.action("github_operand_input")
def handle_github_operand_input(ack):
    """Acknowledge GitHub operand input action."""
    ack()


@app.action("slack_history_select")
def handle_slack_history_select(ack):
    """Acknowledge Slack history select action."""
    ack()


@app.action("github_issues_checkbox")
def handle_github_issues_checkbox(ack):
    """Acknowledge GitHub issues checkbox action."""
    ack()


@app.action("open_config_modal")
def handle_open_config_button(ack, body, client: WebClient):
    """Handle the configure button click."""
    ack()
    channel_id = body["actions"][0]["value"]
    trigger_id = body["trigger_id"]
    open_config_modal(client, trigger_id, channel_id)


@app.view("config_modal")
def handle_config_submit(ack, body, client: WebClient, view):
    """Handle configuration modal submission."""
    ack()
    
    channel_id = view["private_metadata"]
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    
    # Extract values
    docs_urls_raw = values.get("docs_urls", {}).get("docs_urls_input", {}).get("value", "") or ""
    docs_urls = [url.strip() for url in docs_urls_raw.split("\n") if url.strip()]
    
    github_operator = values.get("github_operator", {}).get("github_operator_input", {}).get("value", "")
    github_operand = values.get("github_operand", {}).get("github_operand_input", {}).get("value", "")
    
    # Check if GitHub issues should be included
    github_issues_selected = values.get("github_issues", {}).get("github_issues_checkbox", {}).get("selected_options", [])
    include_github_issues = len(github_issues_selected) > 0
    
    slack_history_option = values.get("slack_history_days", {}).get("slack_history_select", {}).get("selected_option")
    slack_history_days = int(slack_history_option["value"]) if slack_history_option else 30
    
    db = next(get_db())
    
    try:
        # Get workspace info from auth.test (no extra scope needed)
        auth_info = client.auth_test()
        team_id = auth_info["team_id"]
        team_name = auth_info.get("team", team_id)  # Fallback to ID if name not available
        
        workspace = db.query(Workspace).filter_by(slack_team_id=team_id).first()
        if not workspace:
            workspace = Workspace(slack_team_id=team_id, slack_team_name=team_name)
            db.add(workspace)
            db.flush()
        
        # Get or create channel
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]
        
        channel = db.query(MonitoredChannel).filter_by(slack_channel_id=channel_id).first()
        if not channel:
            channel = MonitoredChannel(
                workspace_id=workspace.id,
                slack_channel_id=channel_id,
                slack_channel_name=channel_name
            )
            db.add(channel)
            db.flush()
        else:
            # Clear existing sources for reconfiguration
            db.query(KnowledgeSource).filter_by(channel_id=channel.id).delete()
        
        # Add knowledge sources
        sources = []
        
        # Documentation URLs (multiple)
        for doc_url in docs_urls:
            sources.append(KnowledgeSource(
                channel_id=channel.id,
                source_type=SourceType.DOCUMENTATION,
                url=doc_url,
                status=SourceStatus.PENDING
            ))
        
        if github_operator:
            sources.append(KnowledgeSource(
                channel_id=channel.id,
                source_type=SourceType.GITHUB_OPERATOR,
                url=github_operator,
                status=SourceStatus.PENDING
            ))
            
            # Add GitHub Issues if checkbox selected
            if include_github_issues:
                sources.append(KnowledgeSource(
                    channel_id=channel.id,
                    source_type=SourceType.GITHUB_ISSUES,
                    url=github_operator,  # Use same repo URL
                    status=SourceStatus.PENDING
                ))
        
        if github_operand:
            sources.append(KnowledgeSource(
                channel_id=channel.id,
                source_type=SourceType.GITHUB_OPERAND,
                url=github_operand,
                status=SourceStatus.PENDING
            ))
        
        if slack_history_days > 0:
            sources.append(KnowledgeSource(
                channel_id=channel.id,
                source_type=SourceType.SLACK_HISTORY,
                url=f"slack://{channel_id}?days={slack_history_days}",
                status=SourceStatus.PENDING
            ))
        
        for source in sources:
            db.add(source)
        
        db.commit()
        
        # Notify user
        client.chat_postMessage(
            channel=channel_id,
            text=(
                f"✅ Configuration saved! Indexing {len(sources)} knowledge source(s)...\n"
                f"This may take a few minutes. I'll let you know when I'm ready!"
            )
        )
        
        # Trigger indexing
        trigger_indexing(channel.id)
        
        console.print(f"[green]Channel {channel_name} configured with {len(sources)} sources[/green]")
        
    except Exception as e:
        console.print(f"[red]Error saving configuration:[/red] {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ Error saving configuration: {str(e)[:100]}"
        )


