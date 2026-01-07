# Forum Replier Bot

An AI-powered Slack bot that answers questions in your internal forums by referencing documentation, GitHub repositories, and channel conversation history.

## Features

- 📚 **Documentation Crawling** - Prefix-scoped crawling (stays within the specified path)
- 🐙 **GitHub Integration** - Operator-aware fetching (CRDs, API types, RBAC, samples)
- 💬 **Slack History** - Index past conversations for context
- 🤖 **Claude AI** - Concise, human-like responses via Vertex AI
- 👍 **Feedback Loop** - Learn from thumbs up/down reactions
- 🧵 **Thread-Aware** - Replies in threads to reduce noise

## Prerequisites

- Python 3.12+
- A Slack workspace with admin access
- Google Cloud project with Claude enabled via Vertex AI
- (Optional) GitHub token for private repos

## Setup

### 1. Clone and Install

```bash
cd forum-replier
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it "Forum Replier" and select your workspace

#### OAuth & Permissions

Add these **Bot Token Scopes**:
- `app_mentions:read` - See when mentioned
- `channels:history` - Read channel messages
- `channels:read` - View channel info
- `chat:write` - Send messages
- `reactions:read` - Track feedback
- `users:read` - Get user info
- `team:read` - Get workspace info

#### Event Subscriptions

Enable events and subscribe to:
- `app_home_opened`
- `app_mention`
- `message.channels`
- `reaction_added`

#### Socket Mode

1. Go to **Socket Mode** in the sidebar
2. Enable Socket Mode
3. Create an App-Level Token with `connections:write` scope
4. Save the token (starts with `xapp-`)

#### Install to Workspace

1. Go to **Install App**
2. Click **Install to Workspace**
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 3. Configure Environment

```bash
cp env.example .env
```

Edit `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_REGION=us-east5
CLAUDE_MODEL=claude-sonnet-4@20250514
```

### 4. Run the Bot

```bash
python -m app.main
```

## Usage

### Configure a Channel

1. Invite the bot to your channel: `/invite @Forum Replier`
2. Mention the bot with "configure": `@Forum Replier configure`
3. Fill in the configuration modal with your knowledge sources

### Ask Questions

Just mention the bot with your question:
```
@Forum Replier how do I create a Certificate resource?
```

### Provide Feedback

React with 👍 or 👎 to bot answers to help improve future responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Slack                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │ Channel │   │ Channel │   │ Channel │   │   ...   │     │
│  │   A     │   │    B    │   │    C    │   │         │     │
│  └────┬────┘   └────┬────┘   └────┬────┘   └─────────┘     │
└───────┼─────────────┼─────────────┼─────────────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │ Socket Mode
                      ▼
        ┌─────────────────────────────┐
        │      Forum Replier Bot      │
        │  ┌───────────────────────┐  │
        │  │   Event Handlers      │  │
        │  │  - Message events     │  │
        │  │  - Reaction tracking  │  │
        │  │  - Config modals      │  │
        │  └───────────┬───────────┘  │
        │              │              │
        │  ┌───────────▼───────────┐  │
        │  │   Query Pipeline      │  │
        │  │  1. Embed question    │  │
        │  │  2. Vector search     │  │
        │  │  3. Generate answer   │  │
        │  └───────────┬───────────┘  │
        │              │              │
        │  ┌───────────▼───────────┐  │
        │  │   Knowledge Store     │  │
        │  │  - ChromaDB vectors   │  │
        │  │  - SQLite metadata    │  │
        │  └───────────────────────┘  │
        └─────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  Docs   │  │ GitHub  │  │ Claude  │
   │ Crawler │  │   API   │  │Vertex AI│
   └─────────┘  └─────────┘  └─────────┘
```

## Troubleshooting

### "invalid_auth" error
Your Slack tokens are incorrect. Re-copy them from the Slack app settings.

### "missing_scope" error
Add the required scope in OAuth & Permissions, reinstall the app, and update your bot token.

### Claude model not found
Check available models in your GCP Vertex AI Model Garden and update `CLAUDE_MODEL` in `.env`.

### Crawler only gets 1 page
Make sure the documentation URL is correct and the site allows crawling.

## License

MIT


