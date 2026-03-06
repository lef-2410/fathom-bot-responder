#!/usr/bin/env python3
"""
Support Assistant - Main entry point.

Polls Gmail inbox for support requests, searches Notion for relevant help articles,
and drafts responses for human review.
"""

import logging
import sys
import time
import signal
from datetime import datetime

from config import Config
from email_client import GmailClient, ProcessedEmailTracker, EmailData
from classifier import classify_email, ClassificationResult
from knowledge_search import search_notion_articles, KnowledgeSearchResult
from composer import compose_response

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received, stopping after current cycle...")
    running = False


def process_email(
    email: EmailData,
    gmail: GmailClient,
    tracker: ProcessedEmailTracker
) -> bool:
    """
    Process a single email through the support pipeline.

    Args:
        email: The email to process
        gmail: Gmail client for saving drafts
        tracker: Tracker for processed emails

    Returns:
        True if a draft was created, False otherwise
    """
    logger.info(f"Processing email: {email}")

    # Step 1: Classify the email
    logger.info("Classifying email...")
    classification = classify_email(email)

    if not classification.is_support_request:
        logger.info(f"Email is not a support request: {classification.summary}")
        tracker.mark_processed(email.message_id)
        return False

    logger.info(f"Support request detected: {classification.category} - {classification.summary}")

    # Step 2: Search for relevant help articles
    logger.info("Searching for relevant help articles...")
    knowledge = search_notion_articles(email, classification)

    if knowledge.articles:
        logger.info(f"Found {len(knowledge.articles)} relevant article(s)")
        for article in knowledge.articles:
            logger.debug(f"  - {article.title}: {article.url}")
    else:
        logger.info("No relevant articles found")

    # Step 3: Compose response
    logger.info("Composing response...")
    draft = compose_response(email, classification, knowledge)

    # Step 4: Save draft to Gmail
    logger.info("Saving draft to Gmail...")
    success = gmail.save_draft(
        to_address=email.sender,
        subject=draft.subject,
        body=draft.body,
        in_reply_to=email.message_id
    )

    if success:
        logger.info(f"Draft saved successfully for email from {email.sender}")
        tracker.mark_processed(email.message_id)
        return True
    else:
        logger.error(f"Failed to save draft for email from {email.sender}")
        return False


def run_single_cycle(gmail: GmailClient, tracker: ProcessedEmailTracker) -> dict:
    """
    Run a single cycle of email processing.

    Returns:
        Statistics dict with counts of processed/skipped/drafted emails
    """
    stats = {
        "fetched": 0,
        "already_processed": 0,
        "not_support": 0,
        "drafts_created": 0,
        "errors": 0
    }

    try:
        # Fetch unread emails
        emails = gmail.fetch_unread_emails()
        stats["fetched"] = len(emails)

        if not emails:
            logger.debug("No unread emails found")
            return stats

        logger.info(f"Found {len(emails)} unread email(s)")

        for email in emails:
            # Skip already processed emails
            if tracker.is_processed(email.message_id):
                logger.debug(f"Skipping already processed email: {email.message_id}")
                stats["already_processed"] += 1
                continue

            try:
                draft_created = process_email(email, gmail, tracker)
                if draft_created:
                    stats["drafts_created"] += 1
                else:
                    stats["not_support"] += 1
            except Exception as e:
                logger.error(f"Error processing email {email.uid}: {e}")
                stats["errors"] += 1
                continue

    except Exception as e:
        logger.error(f"Error during email fetch: {e}")
        stats["errors"] += 1

    return stats


def main():
    """Main entry point for the support assistant."""
    global running

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "=" * 60)
    print("  Support Assistant")
    print("=" * 60)

    # Validate configuration
    errors = Config.validate()
    if errors:
        print("\nConfiguration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file and try again.")
        sys.exit(1)

    print(Config.display())

    # Initialize tracker
    tracker = ProcessedEmailTracker()
    print(f"Loaded {tracker.count()} previously processed email IDs\n")

    print(f"Starting polling loop (every {Config.POLL_INTERVAL_SECONDS} seconds)")
    print("Press Ctrl+C to stop\n")

    cycle_count = 0

    while running:
        cycle_count += 1
        cycle_start = datetime.now()

        print(f"\n--- Cycle {cycle_count} at {cycle_start.strftime('%H:%M:%S')} ---")

        try:
            with GmailClient() as gmail:
                stats = run_single_cycle(gmail, tracker)

            # Print cycle summary
            print(f"  Emails fetched: {stats['fetched']}")
            if stats['fetched'] > 0:
                print(f"  Already processed: {stats['already_processed']}")
                print(f"  Not support requests: {stats['not_support']}")
                print(f"  Drafts created: {stats['drafts_created']}")
                if stats['errors'] > 0:
                    print(f"  Errors: {stats['errors']}")

        except RuntimeError as e:
            logger.error(f"Runtime error: {e}")
            print(f"  Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in cycle: {e}")
            print(f"  Unexpected error: {e}")

        # Wait for next cycle (unless shutting down)
        if running:
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            sleep_time = max(0, Config.POLL_INTERVAL_SECONDS - cycle_duration)

            if sleep_time > 0:
                logger.debug(f"Sleeping for {sleep_time:.1f} seconds")
                # Sleep in small increments to respond to shutdown quickly
                for _ in range(int(sleep_time)):
                    if not running:
                        break
                    time.sleep(1)

    print("\n" + "=" * 60)
    print("  Support Assistant stopped")
    print("=" * 60)


if __name__ == "__main__":
    main()
