"""Cloud Bot — polls Fathom and automates post-call workflows."""

import logging
import signal
import time
from datetime import datetime

from app.config import Config
from app.style_guide import load_style_guide
from app.fathom_client import fetch_recent_meetings, parse_meeting, is_internal_call
from app.notion_client import check_existing, create_page, load_existing_recording_ids
from app.gmail_client import save_draft
from app.call_analyzer import analyze_call, draft_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Graceful shutdown
running = True

# In-memory set of recording IDs we've already processed.
# Seeded from Notion at startup, updated immediately after each new page creation.
# This prevents duplicates caused by Notion API eventual consistency.
processed_ids: set[str] = set()


def signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received, stopping after current cycle...")
    running = False


def run_cycle(style_guide: str) -> dict:
    """Run one polling cycle: fetch meetings, process new ones."""
    global processed_ids
    stats = {
        "fetched": 0,
        "skipped_internal": 0,
        "skipped_duplicate": 0,
        "processed": 0,
        "errors": 0,
    }

    # 1. Fetch recent meetings from Fathom
    try:
        raw_meetings = fetch_recent_meetings(limit=20)
    except Exception as e:
        logger.error(f"Fathom API error: {e}")
        stats["errors"] += 1
        return stats

    stats["fetched"] = len(raw_meetings)
    logger.info(f"Fetched {len(raw_meetings)} meetings from Fathom")

    for raw in raw_meetings:
        call = parse_meeting(raw)

        # 2. Skip internal calls
        if is_internal_call(call.title):
            stats["skipped_internal"] += 1
            continue

        # 3. Skip if no date (can't dedup or log properly)
        if not call.date:
            logger.warning(f"Skipping call with no date: {call.title}")
            stats["errors"] += 1
            continue

        # 4. Dedup — check in-memory cache FIRST (instant, no consistency lag)
        if call.recording_id and call.recording_id in processed_ids:
            stats["skipped_duplicate"] += 1
            continue

        # 5. Dedup — then check Notion as backup (catches manually-logged entries)
        try:
            if check_existing(call.recording_id, call.title, call.date):
                # Add to in-memory cache so we don't re-query next cycle
                if call.recording_id:
                    processed_ids.add(call.recording_id)
                stats["skipped_duplicate"] += 1
                continue
        except Exception as e:
            logger.error(f"Notion dedup error for '{call.title}': {e}")
            stats["errors"] += 1
            continue

        # 6. Process this call
        try:
            logger.info(f"Processing: {call.title} ({call.date})")

            # Analyze with Claude
            analyzed = analyze_call(call)
            subject, body = draft_email(analyzed, style_guide)
            analyzed.email_subject = subject
            analyzed.email_body = body

            # Create Notion page
            page_url = create_page(analyzed)

            # Immediately mark as processed in memory (prevents duplicates
            # even if Notion hasn't indexed the new page yet)
            if call.recording_id:
                processed_ids.add(call.recording_id)

            # Collect all external invitee emails for the To field
            invitee_emails = [
                p["email"] for p in call.participants
                if p.get("email")
                and p.get("is_external", True)
                and p["email"].lower() != Config.GMAIL_ADDRESS.lower()
            ]
            # Fall back to Claude-extracted contact email if no invitees found
            if not invitee_emails and analyzed.contact_email:
                invitee_emails = [analyzed.contact_email]

            if invitee_emails:
                draft_ok = save_draft(invitee_emails, subject, body)
                if draft_ok:
                    logger.info(f"Draft saved for {', '.join(invitee_emails)}")
                else:
                    logger.warning(f"Draft save failed for {', '.join(invitee_emails)}")
            else:
                logger.warning(f"No contact emails for '{call.title}', skipping draft")

            stats["processed"] += 1
            logger.info(
                f"Done: {analyzed.company_name} | {analyzed.contact_name} | "
                f"Sentiment: {analyzed.sentiment} | {page_url}"
            )

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error processing '{call.title}': {e}", exc_info=True)

    return stats


def main():
    global running, processed_ids
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Validate config
    Config.validate()

    # Set log level from config
    logging.getLogger().setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

    # Load style guide once at startup
    style_guide = load_style_guide()

    # Seed the in-memory dedup cache from Notion
    processed_ids = load_existing_recording_ids()

    logger.info("=" * 50)
    logger.info("  Cloud Bot starting")
    logger.info(f"  Polling every {Config.POLL_INTERVAL_SECONDS}s ({Config.POLL_INTERVAL_SECONDS // 60} min)")
    logger.info(f"  Gmail: {Config.GMAIL_ADDRESS}")
    logger.info(f"  Notion DB: {Config.NOTION_DATABASE_ID[:8]}...")
    logger.info(f"  Known recordings: {len(processed_ids)}")
    logger.info("=" * 50)

    cycle_count = 0

    while running:
        cycle_count += 1
        cycle_start = datetime.now()
        logger.info(f"--- Cycle {cycle_count} at {cycle_start.strftime('%H:%M:%S')} ---")

        try:
            stats = run_cycle(style_guide)
            logger.info(
                f"Cycle {cycle_count} done: "
                f"fetched={stats['fetched']} "
                f"internal={stats['skipped_internal']} "
                f"duplicate={stats['skipped_duplicate']} "
                f"processed={stats['processed']} "
                f"errors={stats['errors']}"
            )
        except Exception as e:
            logger.error(f"Cycle {cycle_count} failed: {e}", exc_info=True)

        # Interruptible sleep
        if running:
            elapsed = (datetime.now() - cycle_start).total_seconds()
            sleep_time = max(0, Config.POLL_INTERVAL_SECONDS - elapsed)
            logger.debug(f"Sleeping {sleep_time:.0f}s until next cycle")
            for _ in range(int(sleep_time)):
                if not running:
                    break
                time.sleep(1)

    logger.info("Cloud Bot stopped")


if __name__ == "__main__":
    main()
