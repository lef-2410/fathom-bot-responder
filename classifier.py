"""
Email classifier module for Support Assistant.
Uses Claude CLI to determine if an email is an actionable support request.
"""

import subprocess
import json
import logging
from dataclasses import dataclass
from typing import Optional

from email_client import EmailData
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of email classification."""
    is_support_request: bool
    confidence: str  # "high", "medium", "low"
    category: Optional[str]  # e.g., "technical", "billing", "general", "feature_request"
    summary: str  # Brief summary of what the user needs help with
    raw_response: str


def has_support_keywords(email: EmailData) -> bool:
    """Quick pre-filter to check if email contains support-related keywords."""
    text = f"{email.subject} {email.body}".lower()
    return any(keyword in text for keyword in Config.SUPPORT_KEYWORDS)


def classify_email(email: EmailData) -> ClassificationResult:
    """
    Use Claude CLI to classify if an email is an actionable support request.

    Args:
        email: The email to classify

    Returns:
        ClassificationResult with classification details
    """
    # First, do a quick keyword pre-filter
    if not has_support_keywords(email):
        logger.debug(f"Email {email.uid} doesn't contain support keywords, skipping Claude classification")
        return ClassificationResult(
            is_support_request=False,
            confidence="high",
            category=None,
            summary="No support-related keywords detected",
            raw_response=""
        )

    # Prepare the prompt for Claude
    prompt = f"""Analyze this email and determine if it's an actionable support request that needs a response.

EMAIL DETAILS:
From: {email.sender_name} <{email.sender}>
Subject: {email.subject}
Date: {email.date}

BODY:
{email.body[:2000]}  # Truncate very long emails

INSTRUCTIONS:
1. Determine if this is a genuine support request (someone asking for help with a product/service)
2. Exclude: spam, marketing, newsletters, automated notifications, personal emails, job applications
3. Focus on emails where someone is asking a question or reporting a problem

Respond with ONLY a JSON object in this exact format:
{{
    "is_support_request": true/false,
    "confidence": "high/medium/low",
    "category": "technical/billing/general/feature_request/other" or null,
    "summary": "Brief 1-2 sentence summary of what the user needs help with"
}}

If not a support request, set category to null and summary to a brief reason why."""

    try:
        # Call Claude CLI in print mode
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr}")
            # Fall back to keyword-based classification
            return ClassificationResult(
                is_support_request=True,  # Err on the side of caution
                confidence="low",
                category="general",
                summary="Classification failed, marked for manual review",
                raw_response=result.stderr
            )

        raw_response = result.stdout.strip()
        logger.debug(f"Claude response: {raw_response}")

        # Parse the JSON response
        # Find JSON in the response (Claude might include extra text)
        json_start = raw_response.find("{")
        json_end = raw_response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = raw_response[json_start:json_end]
            data = json.loads(json_str)

            return ClassificationResult(
                is_support_request=data.get("is_support_request", False),
                confidence=data.get("confidence", "low"),
                category=data.get("category"),
                summary=data.get("summary", ""),
                raw_response=raw_response
            )
        else:
            logger.warning(f"Could not find JSON in Claude response: {raw_response}")
            return ClassificationResult(
                is_support_request=True,
                confidence="low",
                category="general",
                summary="Could not parse classification, marked for manual review",
                raw_response=raw_response
            )

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return ClassificationResult(
            is_support_request=True,
            confidence="low",
            category="general",
            summary="Classification timed out, marked for manual review",
            raw_response="TIMEOUT"
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return ClassificationResult(
            is_support_request=True,
            confidence="low",
            category="general",
            summary="JSON parse error, marked for manual review",
            raw_response=raw_response if 'raw_response' in dir() else str(e)
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found. Please install it from https://claude.ai/code")
        raise RuntimeError("Claude CLI is not installed or not in PATH")
    except Exception as e:
        logger.error(f"Unexpected error during classification: {e}")
        return ClassificationResult(
            is_support_request=True,
            confidence="low",
            category="general",
            summary=f"Error during classification: {str(e)[:100]}",
            raw_response=str(e)
        )
