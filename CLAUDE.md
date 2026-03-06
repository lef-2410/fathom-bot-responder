# Call Workflow Assistant

This project automates post-call workflows for customer success calls.

## Email Voice & Style
CRITICAL: Before drafting any follow-up email, read `.claude/email-style.md` in full.
Match the style examples exactly. The email must sound like Laura wrote it, not an AI.

## Notion Call Tracker
The Call Tracker database ID is stored as `NOTION_CALL_TRACKER_ID` in the `.env` file.
If that key is missing, the database has not been created yet — create it on the first
`/log-call` run, then add the ID to `.env`.

Use these MCP tools for Notion:
- `notion-create-database` — create the Call Tracker on first run
- `notion-create-pages` — add a new call record
- `notion-search` — find existing records
- `notion-fetch` — read full page content
- `notion-update-page` — update existing records

## Gmail Drafts
Follow-up emails are created as Gmail drafts via Chrome browser automation.
NEVER send automatically. Always save as draft for Laura to review.

Steps: navigate to mail.google.com → click Compose → fill To, Subject, Body →
keyboard shortcut to save draft (Cmd+Shift+D or close compose window to auto-save).

## User Identity
- Name: Laura
- Sign-off: Laura (first name only, no title)
- Company: 1mind
- Email: stored in `.env` as `GMAIL_ADDRESS`

## Commands Available
- `/log-call` — log a call, create Notion entry, draft follow-up email
- `/weekly-summary` — aggregate all calls from the week into a digest email draft
- `/add-style-example` — add a real email you wrote to train the style guide
- `/view-account` — look up call history for a specific company
