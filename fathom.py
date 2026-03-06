#!/usr/bin/env python3
"""
Fetch the latest call summary from the Fathom API.
Usage:
  python fathom.py            # print most recent call
  python fathom.py --list 5   # list the 5 most recent calls
  python fathom.py --id <id>  # fetch a specific meeting by ID
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env already loaded or not needed

API_KEY = os.getenv("FATHOM_API_KEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
BASE_URL = "https://api.fathom.ai/external/v1"


def get_headers():
    if not API_KEY:
        print("ERROR: FATHOM_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return {"X-Api-Key": API_KEY, "Accept": "application/json"}


def fetch_meetings(limit=1):
    params = {"limit": limit, "include_summary": "true"}
    if GMAIL_ADDRESS:
        params["recorded_by[]"] = GMAIL_ADDRESS
    resp = requests.get(
        f"{BASE_URL}/meetings",
        headers=get_headers(),
        params=params,
        timeout=15,
    )
    if resp.status_code == 401:
        print("ERROR: Invalid Fathom API key.", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def fetch_meeting(meeting_id):
    """Fetch a single meeting by recording_id by searching the list."""
    meeting_id = str(meeting_id)
    # Fetch up to 50 to find the right one
    params = {"limit": 50, "include_summary": "true"}
    if GMAIL_ADDRESS:
        params["recorded_by[]"] = GMAIL_ADDRESS
    resp = requests.get(
        f"{BASE_URL}/meetings",
        headers=get_headers(),
        params=params,
        timeout=15,
    )
    if resp.status_code == 401:
        print("ERROR: Invalid Fathom API key.", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    data = resp.json()
    meetings = data if isinstance(data, list) else (
        data.get("items") or data.get("data") or data.get("meetings") or []
    )
    for m in meetings:
        if str(m.get("recording_id") or m.get("id") or "") == meeting_id:
            return m
    print(f"ERROR: Meeting ID {meeting_id} not found in your recent calls.", file=sys.stderr)
    sys.exit(1)


def format_date(iso_string):
    if not iso_string:
        return "Unknown date"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_string


def format_meeting(m):
    title = m.get("title") or m.get("meeting_title") or "Untitled Meeting"
    date = format_date(
        m.get("scheduled_start_time") or
        m.get("recording_start_time") or
        m.get("started_at") or
        m.get("created_at")
    )
    url = m.get("url") or m.get("recording_url") or ""

    # Participants — Fathom uses "calendar_invitees" but also check other keys
    participants = (
        m.get("calendar_invitees") or
        m.get("participants") or
        m.get("attendees") or []
    )
    participant_names = []
    participant_emails = []
    for p in participants:
        name = p.get("name") or p.get("full_name") or ""
        email = p.get("email") or ""
        is_external = p.get("is_external", True)
        if name and is_external:  # only external attendees (i.e. the customer)
            participant_names.append(name)
        if email and is_external:
            participant_emails.append(email)

    # Summary
    summary = ""
    default_summary = m.get("default_summary") or m.get("summary") or {}
    if isinstance(default_summary, dict):
        summary = (
            default_summary.get("markdown_formatted") or
            default_summary.get("markdown") or
            default_summary.get("text") or ""
        )
    elif isinstance(default_summary, str):
        summary = default_summary

    # Action items
    action_items = m.get("action_items") or []
    action_lines = []
    for item in action_items:
        if isinstance(item, dict):
            desc = item.get("description") or item.get("text") or str(item)
        else:
            desc = str(item)
        action_lines.append(f"- {desc}")

    # Build output
    lines = [
        f"Meeting: {title}",
        f"Date: {date}",
    ]
    if participant_names:
        lines.append(f"Participants: {', '.join(participant_names)}")
    if participant_emails:
        lines.append(f"Emails: {', '.join(participant_emails)}")
    if url:
        lines.append(f"Recording: {url}")
    lines.append("")

    if summary:
        lines.append("## Summary")
        lines.append(summary.strip())
        lines.append("")

    if action_lines:
        lines.append("## Action Items")
        lines.extend(action_lines)
        lines.append("")

    return "\n".join(lines)


def list_meetings(data):
    meetings = data if isinstance(data, list) else (
        data.get("items") or data.get("data") or data.get("meetings") or []
    )
    if not meetings:
        print("No meetings found.")
        return
    print(f"{'#':<4} {'Date':<12} {'Title':<50} {'ID'}")
    print("-" * 90)
    for i, m in enumerate(meetings, 1):
        date = format_date(m.get("started_at") or m.get("created_at"))
        title = (m.get("title") or "Untitled")[:48]
        mid = m.get("recording_id") or m.get("id") or ""
        print(f"{i:<4} {date:<12} {title:<50} {mid}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Fathom call summaries")
    parser.add_argument("--list", metavar="N", type=int, nargs="?", const=10,
                        help="List N most recent meetings (default 10)")
    parser.add_argument("--id", metavar="MEETING_ID", help="Fetch a specific meeting by ID")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.id:
        m = fetch_meeting(args.id)
        if args.json:
            print(json.dumps(m, indent=2))
        else:
            print(format_meeting(m))
        return

    limit = args.list if args.list else 1
    data = fetch_meetings(limit=limit)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    meetings = data if isinstance(data, list) else (
        data.get("items") or data.get("data") or data.get("meetings") or []
    )

    if args.list:
        list_meetings(data)
        return

    # Default: print the most recent meeting formatted for /log-call
    if not meetings:
        print("No meetings found in Fathom.")
        sys.exit(0)

    print(format_meeting(meetings[0]))


if __name__ == "__main__":
    main()
