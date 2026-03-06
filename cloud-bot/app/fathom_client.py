"""Fathom API client — fetches and parses meeting data."""

import logging
from datetime import datetime, timezone

import requests

from app.config import Config
from app.models import CallData

logger = logging.getLogger(__name__)

BASE_URL = "https://api.fathom.ai/external/v1"


def _headers():
    return {"X-Api-Key": Config.FATHOM_API_KEY, "Accept": "application/json"}


def fetch_recent_meetings(limit: int = 20) -> list[dict]:
    """Fetch recent meetings from Fathom, filtered to Laura's recordings."""
    params = {"limit": limit, "include_summary": "true"}
    if Config.GMAIL_ADDRESS:
        params["recorded_by[]"] = Config.GMAIL_ADDRESS

    resp = requests.get(
        f"{BASE_URL}/meetings",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # Fathom wraps results in different envelope keys depending on version
    meetings = data if isinstance(data, list) else (
        data.get("items") or data.get("data") or data.get("meetings") or []
    )
    return meetings


def _format_date(iso_string: str) -> str:
    """Convert ISO timestamp to YYYY-MM-DD."""
    if not iso_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_string[:10] if len(iso_string) >= 10 else iso_string


def _compute_call_week(date_str: str) -> str:
    """Convert YYYY-MM-DD to ISO week like '2026-W09'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    except Exception:
        return ""


def parse_meeting(m: dict) -> CallData:
    """Parse a raw Fathom meeting dict into a CallData object."""
    title = m.get("title") or m.get("meeting_title") or "Untitled Meeting"
    date = _format_date(
        m.get("scheduled_start_time")
        or m.get("recording_start_time")
        or m.get("started_at")
        or m.get("created_at")
        or ""
    )
    recording_url = m.get("url") or m.get("recording_url") or ""
    recording_id = str(m.get("recording_id") or m.get("id") or "")

    # Participants
    raw_participants = (
        m.get("calendar_invitees")
        or m.get("participants")
        or m.get("attendees")
        or []
    )
    participants = []
    for p in raw_participants:
        name = p.get("name") or p.get("full_name") or ""
        email = p.get("email") or ""
        is_external = p.get("is_external", True)
        participants.append({
            "name": name,
            "email": email,
            "is_external": is_external,
        })

    # Summary
    summary = ""
    default_summary = m.get("default_summary") or m.get("summary") or {}
    if isinstance(default_summary, dict):
        summary = (
            default_summary.get("markdown_formatted")
            or default_summary.get("markdown")
            or default_summary.get("text")
            or ""
        )
    elif isinstance(default_summary, str):
        summary = default_summary

    # Action items
    raw_actions = m.get("action_items") or []
    action_items = []
    for item in raw_actions:
        if isinstance(item, dict):
            desc = item.get("description") or item.get("text") or str(item)
        else:
            desc = str(item)
        action_items.append(desc)

    return CallData(
        recording_id=recording_id,
        title=title,
        date=date,
        call_week=_compute_call_week(date),
        recording_url=recording_url,
        participants=participants,
        summary_text=summary.strip(),
        action_items=action_items,
    )


def is_internal_call(title: str) -> bool:
    """Returns True if the call title contains the [INT] marker."""
    return "[INT]" in title
