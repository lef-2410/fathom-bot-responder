"""Loads the email style guide for use in Anthropic API prompts."""

import os
import logging

from app.config import Config

logger = logging.getLogger(__name__)

_STYLE_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "..", "email-style.md")


def _fallback_guide() -> str:
    """Generate a fallback style guide using config values."""
    name = Config.USER_NAME or "the user"
    company = Config.COMPANY_NAME or "the company"
    return f"""# Email Style Guide

## Writing Style
- Write as "I" — never "we" or corporate voice
- Short paragraphs, 2–3 sentences max
- Warm but not effusive — no "Hope this finds you well!"
- Gets to the point quickly — no long preamble
- Action items in a short bullet list, everything else in prose
- Brief, natural sign-off

## What to Avoid
- "I hope this email finds you well"
- "Please don't hesitate to reach out"
- "As per our conversation"
- "Going forward"
- "Best regards" — just sign as {name}
- Passive voice
- Long walls of text
- Generic filler sentences that don't add information

## Sign-off Format
[brief closing line]

{name}

## Drafting Instruction
Write as {name}, a customer success manager at {company}. The email should feel
like it came from a real person who was genuinely on the call — specific,
warm, and to the point. Reference actual things discussed. Never sound like
a template.

Subject line format: Follow-up from our call, [First Name]
"""


def load_style_guide() -> str:
    """Load the email style guide from file, with fallback to defaults."""
    try:
        with open(_STYLE_GUIDE_PATH, "r") as f:
            content = f.read().strip()
            if content:
                logger.info("Email style guide loaded from file")
                return content
    except FileNotFoundError:
        pass

    logger.warning("Style guide file not found, using fallback defaults")
    return _fallback_guide()
