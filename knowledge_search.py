"""
Knowledge search module for Support Assistant.
Uses Claude CLI with Notion MCP tools to search for relevant help articles.
"""

import subprocess
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, List

from email_client import EmailData
from classifier import ClassificationResult

logger = logging.getLogger(__name__)


@dataclass
class HelpArticle:
    """Represents a relevant help article found in Notion."""
    title: str
    url: str
    relevance_summary: str  # Why this article is relevant


@dataclass
class KnowledgeSearchResult:
    """Result of searching for relevant knowledge base articles."""
    articles: List[HelpArticle]
    search_query: str
    raw_response: str


def search_notion_articles(
    email: EmailData,
    classification: ClassificationResult
) -> KnowledgeSearchResult:
    """
    Search Notion for relevant help articles using Claude CLI with Notion MCP tools.

    Args:
        email: The support email to find articles for
        classification: The classification result with summary

    Returns:
        KnowledgeSearchResult with found articles
    """
    # Build a search query based on the email and classification
    search_context = f"""
Subject: {email.subject}
Category: {classification.category or 'general'}
Summary: {classification.summary}

Key details from email:
{email.body[:1000]}
"""

    prompt = f"""I need to find relevant help articles in Notion for a customer support request.

SUPPORT REQUEST CONTEXT:
{search_context}

INSTRUCTIONS:
1. Use the notion-search tool to search for help articles, documentation, or FAQ entries that could help answer this customer's question
2. Search for 2-3 different relevant queries based on the customer's issue
3. Look for articles that directly address the customer's problem

After searching, respond with ONLY a JSON object in this exact format:
{{
    "search_query": "the main search terms you used",
    "articles": [
        {{
            "title": "Article Title",
            "url": "https://notion.so/...",
            "relevance_summary": "Brief explanation of why this article is relevant"
        }}
    ]
}}

If no relevant articles are found, return an empty articles array.
Only include articles that are genuinely relevant to the support request."""

    # Define allowed Notion tools for the search
    allowed_tools = [
        "mcp__aab54313-9191-4625-ae2b-4e04364c4cbe__notion-search",
        "mcp__aab54313-9191-4625-ae2b-4e04364c4cbe__notion-fetch"
    ]

    try:
        # Call Claude CLI with Notion MCP tools enabled
        cmd = [
            "claude",
            "-p", prompt,
            "--allowedTools", ",".join(allowed_tools)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # Allow more time for Notion searches
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error during knowledge search: {result.stderr}")
            return KnowledgeSearchResult(
                articles=[],
                search_query="",
                raw_response=result.stderr
            )

        raw_response = result.stdout.strip()
        logger.debug(f"Knowledge search response: {raw_response[:500]}...")

        # Parse the JSON response
        json_start = raw_response.rfind("{")
        json_end = raw_response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            # Try to find the last complete JSON object (the final response)
            json_str = raw_response[json_start:json_end]

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to find JSON with articles array
                match = re.search(r'\{[^{}]*"articles"\s*:\s*\[[^\]]*\][^{}]*\}', raw_response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    raise

            articles = []
            for article_data in data.get("articles", []):
                articles.append(HelpArticle(
                    title=article_data.get("title", "Untitled"),
                    url=article_data.get("url", ""),
                    relevance_summary=article_data.get("relevance_summary", "")
                ))

            return KnowledgeSearchResult(
                articles=articles,
                search_query=data.get("search_query", ""),
                raw_response=raw_response
            )
        else:
            logger.warning("Could not find JSON in knowledge search response")
            return KnowledgeSearchResult(
                articles=[],
                search_query="",
                raw_response=raw_response
            )

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out during knowledge search")
        return KnowledgeSearchResult(
            articles=[],
            search_query="",
            raw_response="TIMEOUT"
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in knowledge search: {e}")
        return KnowledgeSearchResult(
            articles=[],
            search_query="",
            raw_response=raw_response if 'raw_response' in dir() else str(e)
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        raise RuntimeError("Claude CLI is not installed or not in PATH")
    except Exception as e:
        logger.error(f"Unexpected error during knowledge search: {e}")
        return KnowledgeSearchResult(
            articles=[],
            search_query="",
            raw_response=str(e)
        )


def format_articles_for_response(articles: List[HelpArticle]) -> str:
    """Format found articles into a string for inclusion in email response."""
    if not articles:
        return ""

    lines = ["Here are some resources that might help:\n"]
    for i, article in enumerate(articles, 1):
        lines.append(f"{i}. {article.title}")
        lines.append(f"   {article.url}")
        if article.relevance_summary:
            lines.append(f"   ({article.relevance_summary})")
        lines.append("")

    return "\n".join(lines)
