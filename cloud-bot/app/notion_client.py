"""Notion REST API client — creates pages and checks for duplicates."""

import logging

import requests

from app.config import Config
from app.models import AnalyzedCall

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"


def _headers():
    return {
        "Authorization": f"Bearer {Config.NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _truncate(text: str, limit: int = 2000) -> str:
    """Notion rich_text blocks have a 2000-char limit."""
    return text[:limit] if text else ""


def load_existing_recording_ids() -> set[str]:
    """Load all Recording IDs already in the Notion database.

    Called once at startup to seed the in-memory dedup cache.
    Paginates through all pages to ensure nothing is missed.
    """
    db_id = Config.NOTION_DATABASE_ID
    ids = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {
            "page_size": 100,
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor

        try:
            resp = requests.post(
                f"{NOTION_API}/databases/{db_id}/query",
                headers=_headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("results", []):
                rec_prop = page.get("properties", {}).get("Recording ID", {})
                rt = rec_prop.get("rich_text", [])
                if rt:
                    rid = rt[0].get("plain_text", "")
                    if rid:
                        ids.add(rid)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        except Exception as e:
            logger.error(f"Failed to load existing recording IDs: {e}")
            break

    logger.info(f"Loaded {len(ids)} existing recording IDs from Notion")
    return ids


def check_existing(recording_id: str, title: str, date: str) -> bool:
    """Check if a call is already logged in Notion.

    Tries Recording ID first (exact match), then falls back to Name + Call Date.
    Returns True if a matching entry exists.
    """
    db_id = Config.NOTION_DATABASE_ID

    # Try by Recording ID first (most reliable)
    if recording_id:
        payload = {
            "filter": {
                "property": "Recording ID",
                "rich_text": {"equals": recording_id},
            }
        }
        try:
            resp = requests.post(
                f"{NOTION_API}/databases/{db_id}/query",
                headers=_headers(),
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                logger.debug(f"Dedup hit on Recording ID: {recording_id}")
                return True
        except Exception as e:
            logger.warning(f"Recording ID dedup query failed: {e}")

    # Fallback: match on Name + Call Date
    if title and date:
        payload = {
            "filter": {
                "and": [
                    {"property": "Name", "title": {"equals": title}},
                    {"property": "Call Date", "date": {"equals": date}},
                ]
            }
        }
        try:
            resp = requests.post(
                f"{NOTION_API}/databases/{db_id}/query",
                headers=_headers(),
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                logger.debug(f"Dedup hit on Name+Date: {title} / {date}")
                return True
        except Exception as e:
            logger.warning(f"Name+Date dedup query failed: {e}")

    return False


def create_page(analyzed: AnalyzedCall) -> str:
    """Create a Notion page in the Call Tracker. Returns the page URL."""
    call = analyzed.call

    properties = {
        "Name": {"title": [{"text": {"content": _truncate(analyzed.company_name)}}]},
        "Contact Name": {"rich_text": [{"text": {"content": _truncate(analyzed.contact_name)}}]},
        "Call Date": {"date": {"start": call.date}},
        "Call Week": {"rich_text": [{"text": {"content": call.call_week}}]},
        "Summary": {"rich_text": [{"text": {"content": _truncate(analyzed.summary)}}]},
        "Pain Points": {"rich_text": [{"text": {"content": _truncate(analyzed.pain_points)}}]},
        "Feature Requests": {"rich_text": [{"text": {"content": _truncate(analyzed.feature_requests)}}]},
        "Sentiment": {"select": {"name": analyzed.sentiment}},
        "Action Items": {"rich_text": [{"text": {"content": _truncate(analyzed.action_items_text)}}]},
        "Next Steps": {"rich_text": [{"text": {"content": _truncate(analyzed.next_steps)}}]},
        "Follow-up Sent": {"checkbox": False},
        "Recording ID": {"rich_text": [{"text": {"content": call.recording_id}}]},
    }

    # Optional fields
    if analyzed.contact_email:
        properties["Contact Email"] = {"email": analyzed.contact_email}

    # Page body: Action Items as checkboxes
    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Action Items"}}]
            },
        }
    ]
    for item in analyzed.action_items_list:
        children.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
                "checked": False,
            },
        })

    # Add recording link to page body
    if call.recording_url:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Recording"}}]
            },
        })
        children.append({
            "object": "block",
            "type": "bookmark",
            "bookmark": {"url": call.recording_url},
        })

    payload = {
        "parent": {"database_id": Config.NOTION_DATABASE_ID},
        "properties": properties,
        "children": children,
    }

    resp = requests.post(
        f"{NOTION_API}/pages",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    page = resp.json()
    page_url = page.get("url", "")
    logger.info(f"Notion page created: {page_url}")
    return page_url
