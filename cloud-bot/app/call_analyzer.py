"""Anthropic API integration — analyzes calls and drafts follow-up emails."""

import json
import logging

import anthropic

from app.config import Config
from app.models import CallData, AnalyzedCall

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


def _get_client():
    return anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)


def _format_participants(participants: list[dict]) -> str:
    """Format participant list for the prompt."""
    external = [p for p in participants if p.get("is_external")]
    if not external:
        return "No external participants listed"
    lines = []
    for p in external:
        name = p.get("name", "Unknown")
        email = p.get("email", "")
        lines.append(f"- {name}" + (f" ({email})" if email else ""))
    return "\n".join(lines)


def analyze_call(call: CallData) -> AnalyzedCall:
    """Use Claude to extract structured data from raw Fathom call data."""
    client = _get_client()

    action_items_str = "\n".join(f"- {item}" for item in call.action_items) if call.action_items else "None listed"

    prompt = f"""Analyze this customer call and extract structured data. Return ONLY valid JSON, no other text.

CALL DETAILS:
Title: {call.title}
Date: {call.date}
Recording: {call.recording_url}

EXTERNAL PARTICIPANTS:
{_format_participants(call.participants)}

CALL SUMMARY:
{call.summary_text}

ACTION ITEMS FROM TRANSCRIPT:
{action_items_str}

Extract the following as a JSON object:
{{
  "company_name": "the customer's company name (infer from meeting title, participants, or summary)",
  "contact_name": "full name of the primary external contact",
  "contact_email": "their email if available from participants, empty string if not",
  "summary": "2-4 sentence narrative of what was discussed",
  "pain_points": "customer frustrations, blockers, or problems mentioned. Use 'None mentioned' if none.",
  "feature_requests": "specific product features requested. Use 'None mentioned' if none.",
  "sentiment": "exactly one of: Very Positive, Positive, Neutral, Mixed, Negative",
  "action_items_text": "plain text list of Laura's commitments, one per line with '- ' prefix",
  "action_items_list": ["item 1", "item 2"],
  "next_steps": "the agreed follow-up plan"
}}

Important:
- company_name should be the customer's company, not 1mind
- contact_name should be the external person, not Laura
- sentiment must be exactly one of the five options listed
- action_items_list should contain each action item as a separate string"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    data = json.loads(raw)

    # Validate sentiment
    valid_sentiments = {"Very Positive", "Positive", "Neutral", "Mixed", "Negative"}
    sentiment = data.get("sentiment", "Neutral")
    if sentiment not in valid_sentiments:
        sentiment = "Neutral"

    return AnalyzedCall(
        call=call,
        company_name=data.get("company_name", call.title),
        contact_name=data.get("contact_name", ""),
        contact_email=data.get("contact_email", ""),
        summary=data.get("summary", ""),
        pain_points=data.get("pain_points", ""),
        feature_requests=data.get("feature_requests", ""),
        sentiment=sentiment,
        action_items_text=data.get("action_items_text", ""),
        action_items_list=data.get("action_items_list", call.action_items),
        next_steps=data.get("next_steps", ""),
    )


def draft_email(analyzed: AnalyzedCall, style_guide: str) -> tuple[str, str]:
    """Use Claude to draft a follow-up email in Laura's voice.

    Returns (subject, body).
    """
    client = _get_client()

    # Extract first name for subject line
    first_name = analyzed.contact_name.split()[0] if analyzed.contact_name else "there"

    prompt = f"""You are Laura, a customer success manager at 1mind.
Draft a follow-up email after this customer call.

EMAIL STYLE GUIDE (follow this exactly):
{style_guide}

CALL CONTEXT:
Company: {analyzed.company_name}
Contact: {analyzed.contact_name}
Date: {analyzed.call.date}
Summary: {analyzed.summary}
Action Items: {analyzed.action_items_text}
Next Steps: {analyzed.next_steps}
Pain Points: {analyzed.pain_points}

EMAIL STRUCTURE:
- Opening: 1 sentence referencing something specific from the call
- Middle: 1-2 sentences on key takeaways or what you discussed
- Action items: short bullet list of Laura's commitments (use "- " bullets)
- Close: 1 line on next steps
- Sign-off: just "Laura" on its own line

Write ONLY the email body text. No subject line, no "Subject:" prefix, no markdown formatting.
Do not include any preamble like "Here's the draft:" — just the email text itself."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    body = response.content[0].text.strip()
    subject = f"Follow-up from our call, {first_name}"

    return subject, body
