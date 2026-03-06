"""Gmail IMAP client — saves follow-up emails as drafts."""

import logging
from email.message import EmailMessage

from imapclient import IMAPClient

from app.config import Config

logger = logging.getLogger(__name__)


def save_draft(to_addresses: list[str] | str, subject: str, body: str) -> bool:
    """Save an email as a draft in Gmail via IMAP.

    Creates a fresh IMAP connection each time (appropriate for 15-min intervals).
    to_addresses can be a list of emails or a single email string.
    Returns True on success, False on failure.
    """
    try:
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]
        to_addresses = [a for a in to_addresses if a]
        if not to_addresses:
            logger.warning("No recipients provided, skipping draft")
            return False

        msg = EmailMessage()
        msg["From"] = Config.GMAIL_ADDRESS
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject
        msg.set_content(body)

        email_bytes = msg.as_bytes()

        client = IMAPClient("imap.gmail.com", port=993, ssl=True)
        client.login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD)
        client.append("[Gmail]/Drafts", email_bytes)
        client.logout()

        logger.info(f"Draft saved: To={', '.join(to_addresses)}, Subject={subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to save draft: {e}")
        return False
