"""
Response composer module for Support Assistant.
Uses Claude CLI to draft helpful support responses.
"""

import subprocess
import logging
from dataclasses import dataclass

from email_client import EmailData
from classifier import ClassificationResult
from knowledge_search import KnowledgeSearchResult, format_articles_for_response

logger = logging.getLogger(__name__)


@dataclass
class DraftResponse:
    """A composed draft response to a support email."""
    subject: str
    body: str
    raw_response: str


def compose_response(
    email: EmailData,
    classification: ClassificationResult,
    knowledge: KnowledgeSearchResult
) -> DraftResponse:
    """
    Use Claude CLI to compose a helpful support response.

    Args:
        email: The original support email
        classification: Classification details
        knowledge: Search results with relevant help articles

    Returns:
        DraftResponse with the composed email
    """
    # Format the articles section if we have any
    articles_section = ""
    if knowledge.articles:
        articles_section = f"""
RELEVANT HELP ARTICLES FOUND:
{format_articles_for_response(knowledge.articles)}

Include links to these articles in your response where appropriate.
"""

    prompt = f"""Compose a helpful, professional support email response.

ORIGINAL EMAIL:
From: {email.sender_name} <{email.sender}>
Subject: {email.subject}
Date: {email.date}

{email.body[:2000]}

CLASSIFICATION:
Category: {classification.category or 'general'}
Summary: {classification.summary}
{articles_section}
INSTRUCTIONS:
1. Write a warm, professional response that addresses the customer's concern
2. Be helpful and empathetic
3. If help articles were found, naturally incorporate links to relevant ones
4. If you don't have enough information to fully answer, acknowledge what you understand and ask clarifying questions
5. Keep the response concise but thorough
6. Sign off professionally

IMPORTANT: Respond with ONLY the email body text. Do not include subject line, headers, or any JSON formatting.
Start directly with a greeting like "Hi [Name]," or "Hello,"

The response will be saved as a draft for human review before sending."""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error during response composition: {result.stderr}")
            # Return a template response for manual editing
            return DraftResponse(
                subject=f"Re: {email.subject}",
                body=_create_fallback_response(email, knowledge),
                raw_response=result.stderr
            )

        raw_response = result.stdout.strip()

        # Clean up the response - remove any JSON wrapper if Claude added one
        body = raw_response

        # If response is wrapped in quotes or JSON, clean it
        if body.startswith('"') and body.endswith('"'):
            body = body[1:-1]
        if body.startswith("```"):
            # Remove markdown code blocks
            lines = body.split("\n")
            body = "\n".join(
                line for line in lines
                if not line.startswith("```")
            )

        # Ensure proper line breaks
        body = body.replace("\\n", "\n")

        return DraftResponse(
            subject=f"Re: {email.subject}",
            body=body.strip(),
            raw_response=raw_response
        )

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out during response composition")
        return DraftResponse(
            subject=f"Re: {email.subject}",
            body=_create_fallback_response(email, knowledge),
            raw_response="TIMEOUT"
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        raise RuntimeError("Claude CLI is not installed or not in PATH")
    except Exception as e:
        logger.error(f"Unexpected error during response composition: {e}")
        return DraftResponse(
            subject=f"Re: {email.subject}",
            body=_create_fallback_response(email, knowledge),
            raw_response=str(e)
        )


def _create_fallback_response(email: EmailData, knowledge: KnowledgeSearchResult) -> str:
    """Create a basic template response when Claude composition fails."""
    articles_text = ""
    if knowledge.articles:
        articles_text = "\n\nIn the meantime, you might find these resources helpful:\n"
        for article in knowledge.articles:
            articles_text += f"- {article.title}: {article.url}\n"

    return f"""Hi {email.sender_name.split()[0] if email.sender_name else 'there'},

Thank you for reaching out to our support team.

[DRAFT - Please review and customize this response]

I've received your message regarding: {email.subject}

[Add your response here]
{articles_text}
Please let me know if you have any other questions.

Best regards,
Support Team

---
[This draft was created automatically and needs review before sending]
"""
