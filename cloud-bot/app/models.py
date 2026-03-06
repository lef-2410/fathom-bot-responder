"""Shared data structures for the cloud bot."""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class CallData:
    """Parsed call data from Fathom."""
    recording_id: str
    title: str
    date: str  # YYYY-MM-DD
    call_week: str  # e.g. "2026-W09"
    recording_url: str
    participants: List[Dict] = field(default_factory=list)
    summary_text: str = ""
    action_items: List[str] = field(default_factory=list)


@dataclass
class AnalyzedCall:
    """Call data after Anthropic API analysis."""
    call: CallData
    company_name: str
    contact_name: str
    contact_email: str
    summary: str
    pain_points: str
    feature_requests: str
    sentiment: str  # Very Positive, Positive, Neutral, Mixed, Negative
    action_items_text: str  # Plain text for Notion property
    action_items_list: List[str] = field(default_factory=list)  # For page body checkboxes
    next_steps: str = ""
    email_subject: str = ""
    email_body: str = ""
