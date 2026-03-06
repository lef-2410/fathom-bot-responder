# Support Assistant

An automated support email assistant that detects support requests, searches Notion for relevant help articles, and drafts responses for human review.

## Features

- Polls Gmail inbox every 5 minutes for new emails
- Uses Claude CLI to classify emails as support requests
- Searches Notion for relevant help articles using MCP tools
- Drafts helpful responses with links to relevant documentation
- Saves drafts to Gmail for human review before sending
- Tracks processed emails to avoid duplicates

## Prerequisites

- Python 3.10+
- [Claude CLI](https://claude.ai/code) installed and authenticated
- Gmail account with IMAP enabled
- Notion workspace (for help article search)

## Setup

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd support-assistant

# Run the setup script
./setup.sh
```

### 2. Configure Gmail

#### Enable IMAP in Gmail:
1. Go to Gmail Settings (gear icon)
2. Click "See all settings"
3. Go to "Forwarding and POP/IMAP" tab
4. Enable IMAP access
5. Save changes

#### Create an App Password:
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication (if not already enabled)
3. Go to https://myaccount.google.com/apppasswords
4. Select "Mail" and your device
5. Click "Generate"
6. Copy the 16-character password (without spaces)

### 3. Configure Environment

Edit the `.env` file with your credentials:

```bash
# Gmail Configuration
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

# Polling interval (default 5 minutes)
POLL_INTERVAL_SECONDS=300

# Optional: Notion database ID for help articles
# NOTION_HELP_DATABASE_ID=your-database-id
```

### 4. Ensure Claude CLI is Authenticated

Make sure Claude CLI is installed and you're logged in:

```bash
# Check Claude CLI is available
claude --version

# Login if needed
claude login
```

## Running the Assistant

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
python main.py
```

Press `Ctrl+C` to stop the assistant gracefully.

## How It Works

1. **Email Fetching**: Polls Gmail inbox for unread emails
2. **Classification**: Uses Claude CLI to determine if an email is a support request
3. **Knowledge Search**: Searches Notion for relevant help articles using MCP tools
4. **Response Drafting**: Uses Claude to compose a helpful response with article links
5. **Draft Saving**: Saves the draft to Gmail's Drafts folder for review

## Project Structure

```
support-assistant/
├── setup.sh              # Setup script for dependencies
├── run.sh                # Runner script
├── .env.example          # Environment template
├── .env                  # Your configuration (not in git)
├── config.py             # Configuration loader
├── email_client.py       # Gmail IMAP client
├── classifier.py         # Email classification using Claude
├── knowledge_search.py   # Notion search using MCP tools
├── composer.py           # Response drafting using Claude
├── main.py               # Main entry point
├── processed_emails.txt  # Tracking file for processed emails
└── README.md             # This file
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_ADDRESS` | Your Gmail address | Required |
| `GMAIL_APP_PASSWORD` | Gmail app password | Required |
| `IMAP_SERVER` | IMAP server address | imap.gmail.com |
| `IMAP_PORT` | IMAP port | 993 |
| `POLL_INTERVAL_SECONDS` | Polling interval in seconds | 300 |
| `SUPPORT_KEYWORDS` | Comma-separated keywords for pre-filtering | help,issue,problem,... |
| `NOTION_HELP_DATABASE_ID` | Optional Notion database ID | None |
| `LOG_LEVEL` | Logging level | INFO |

## Troubleshooting

### "Claude CLI not found"
Install Claude CLI from https://claude.ai/code and ensure it's in your PATH.

### "Login failed" for Gmail
- Verify IMAP is enabled in Gmail settings
- Make sure you're using an App Password, not your regular password
- Check that 2-Factor Authentication is enabled

### No drafts appearing
- Check the Gmail Drafts folder (may take a moment to sync)
- Review logs for any errors during draft saving
- Verify the `[Gmail]/Drafts` folder name matches your locale

### Notion search not working
- Ensure Claude CLI has access to Notion MCP tools
- Verify your Notion workspace is connected to Claude

## Security Notes

- Never commit your `.env` file to version control
- App Passwords can be revoked at any time from Google Account settings
- The assistant only reads emails and creates drafts; it never sends emails automatically
- All drafts require human review before sending
