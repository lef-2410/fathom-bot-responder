# Fathom Bot Responder

Automatically monitors [Fathom](https://fathom.video) for new call recordings, analyzes them with Claude, logs structured data in Notion, and drafts personalized follow-up emails in Gmail.

## How It Works

1. **Polls Fathom** every 15 minutes for new call recordings
2. **Skips internal calls** (any title containing `[INT]`)
3. **Analyzes each call** with Claude to extract company name, contacts, sentiment, action items, pain points, and feature requests
4. **Logs the call** in a Notion Call Tracker database with all structured properties and action item checkboxes
5. **Drafts a follow-up email** via IMAP — addressed to all external invitees, written in your voice using a style guide
6. **Deduplicates** using an in-memory cache seeded from Notion at startup

Emails are saved as **drafts only** — never sent automatically.

## Prerequisites

- Python 3.12+
- [Fathom](https://fathom.video) account with API access
- [Anthropic API](https://console.anthropic.com/) key
- [Notion](https://www.notion.so/my-integrations) integration with a Call Tracker database
- Gmail account with [App Password](https://myaccount.google.com/apppasswords) (requires 2FA)
- [Fly.io](https://fly.io) account (for cloud deployment)

## Setup

### 1. Configure Environment

```bash
cd cloud-bot
cp .env.example .env
```

Edit `.env` with your credentials. See `.env.example` for all available options.

### 2. Set Up Notion

Create a Notion database with these properties:

| Property | Type |
|----------|------|
| Name | Title |
| Call Date | Date |
| Call Week | Text |
| Contact Name | Text |
| Contact Email | Email |
| Summary | Text |
| Pain Points | Text |
| Feature Requests | Text |
| Action Items | Text |
| Next Steps | Text |
| Sentiment | Select (Very Positive, Positive, Neutral, Mixed, Negative) |
| Follow-up Sent | Checkbox |
| Recording ID | Text |

Share the database with your Notion integration.

### 3. Email Style Guide

Create an `email-style.md` file in the `cloud-bot/` directory with examples of your writing style. The bot uses this to draft emails that sound like you. A fallback generic style guide is used if the file is missing.

### 4. Deploy to Fly.io

```bash
cd cloud-bot

# Edit fly.toml — change the app name
# Then create the app:
fly launch --no-deploy --ha=false

# Import secrets from your .env file
fly secrets import < .env

# Deploy (--ha=false ensures only 1 machine — this is a worker, not a web app)
fly deploy --ha=false
```

### 5. Run Locally (optional)

```bash
cd cloud-bot
pip install -r requirements.txt
python -m app.main
```

## Project Structure

```
cloud-bot/
├── app/
│   ├── __init__.py
│   ├── config.py           # Environment variable configuration
│   ├── models.py           # CallData and AnalyzedCall dataclasses
│   ├── fathom_client.py    # Fathom API client
│   ├── call_analyzer.py    # Claude-powered call analysis and email drafting
│   ├── notion_client.py    # Notion REST API client
│   ├── gmail_client.py     # IMAP draft saving
│   ├── style_guide.py      # Email style guide loader
│   └── main.py             # Polling loop and orchestration
├── .env.example            # Environment variable template
├── Dockerfile
├── fly.toml                # Fly.io deployment config
├── requirements.txt
└── build.sh                # Deploy helper script
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `FATHOM_API_KEY` | Fathom API key | Required |
| `NOTION_API_KEY` | Notion integration token | Required |
| `NOTION_DATABASE_ID` | Notion database ID (from URL) | Required |
| `GMAIL_ADDRESS` | Gmail address | Required |
| `GMAIL_APP_PASSWORD` | Gmail app password | Required |
| `USER_NAME` | Your name (used in AI prompts) | Required |
| `COMPANY_NAME` | Your company name (used in AI prompts) | Required |
| `IMAP_SERVER` | IMAP server | `imap.gmail.com` |
| `IMAP_PORT` | IMAP port | `993` |
| `POLL_INTERVAL_SECONDS` | Polling interval in seconds | `900` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Monitoring

```bash
# View live logs
fly logs --app your-app-name

# Check recent logs
fly logs --app your-app-name --no-tail
```

Look for `Known recordings: N` at startup to confirm the dedup cache loaded, and `duplicate=N processed=0` in cycle summaries when there are no new calls.
