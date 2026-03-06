"""
Email client module for Support Assistant.
Handles IMAP connection, fetching emails, and saving drafts to Gmail.
"""

import email
import logging
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from dataclasses import dataclass
from typing import Optional, List, Set
from imapclient import IMAPClient

from config import Config

logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    """Represents a parsed email."""
    uid: int
    message_id: str
    subject: str
    sender: str
    sender_name: str
    body: str
    date: str

    def __str__(self) -> str:
        return f"Email(uid={self.uid}, from={self.sender}, subject={self.subject[:50]}...)"


class GmailClient:
    """Gmail IMAP client for fetching emails and saving drafts."""

    def __init__(self):
        self.server = Config.IMAP_SERVER
        self.port = Config.IMAP_PORT
        self.email_address = Config.GMAIL_ADDRESS
        self.password = Config.GMAIL_APP_PASSWORD
        self._client: Optional[IMAPClient] = None

    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        logger.info(f"Connecting to {self.server}:{self.port}...")
        self._client = IMAPClient(self.server, port=self.port, ssl=True)
        self._client.login(self.email_address, self.password)
        logger.info("Successfully connected to Gmail")

    def disconnect(self) -> None:
        """Close the IMAP connection."""
        if self._client:
            try:
                self._client.logout()
                logger.info("Disconnected from Gmail")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _decode_header_value(self, value: str) -> str:
        """Decode an email header value that might be encoded."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return "".join(result)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract the plain text body from an email message."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        return body.strip()

    def fetch_unread_emails(self) -> List[EmailData]:
        """Fetch all unread emails from the inbox."""
        if not self._client:
            raise RuntimeError("Not connected to server")

        self._client.select_folder("INBOX")
        uids = self._client.search(["UNSEEN"])

        if not uids:
            logger.debug("No unread emails found")
            return []

        logger.info(f"Found {len(uids)} unread email(s)")

        emails = []
        messages = self._client.fetch(uids, ["RFC822", "ENVELOPE"])

        for uid, data in messages.items():
            try:
                raw_email = data[b"RFC822"]
                msg = email.message_from_bytes(raw_email)

                # Parse sender
                sender_raw = msg.get("From", "")
                sender_name, sender_addr = parseaddr(sender_raw)
                sender_name = self._decode_header_value(sender_name)

                # Parse subject
                subject = self._decode_header_value(msg.get("Subject", "(No Subject)"))

                # Get message ID
                message_id = msg.get("Message-ID", f"<uid-{uid}>")

                # Get date
                date_str = msg.get("Date", "")

                # Extract body
                body = self._extract_body(msg)

                email_data = EmailData(
                    uid=uid,
                    message_id=message_id,
                    subject=subject,
                    sender=sender_addr,
                    sender_name=sender_name or sender_addr,
                    body=body,
                    date=date_str
                )
                emails.append(email_data)
                logger.debug(f"Parsed email: {email_data}")

            except Exception as e:
                logger.error(f"Error parsing email UID {uid}: {e}")
                continue

        return emails

    def save_draft(self, to_address: str, subject: str, body: str,
                   in_reply_to: Optional[str] = None) -> bool:
        """
        Save an email as a draft in Gmail's Drafts folder.

        Args:
            to_address: Recipient email address
            subject: Email subject (will prepend 'Re: ' if replying)
            body: Email body text
            in_reply_to: Optional Message-ID of the email being replied to

        Returns:
            True if draft was saved successfully, False otherwise
        """
        if not self._client:
            raise RuntimeError("Not connected to server")

        try:
            # Create the email message
            msg = EmailMessage()
            msg["From"] = self.email_address
            msg["To"] = to_address
            msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
            msg.set_content(body)

            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            # Convert to bytes
            email_bytes = msg.as_bytes()

            # Append to Gmail's Drafts folder
            # Gmail uses "[Gmail]/Drafts" for the drafts folder
            drafts_folder = "[Gmail]/Drafts"

            self._client.append(drafts_folder, email_bytes)
            logger.info(f"Draft saved for reply to {to_address}")
            return True

        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            return False

    def mark_as_read(self, uid: int) -> bool:
        """Mark an email as read."""
        if not self._client:
            raise RuntimeError("Not connected to server")

        try:
            self._client.select_folder("INBOX")
            self._client.add_flags([uid], ["\\Seen"])
            return True
        except Exception as e:
            logger.error(f"Error marking email {uid} as read: {e}")
            return False


class ProcessedEmailTracker:
    """Tracks which emails have already been processed to avoid duplicates."""

    def __init__(self, filepath: str = Config.PROCESSED_EMAILS_FILE):
        self.filepath = filepath
        self._processed = set()  # type: Set[str]
        self._load()

    def _load(self) -> None:
        """Load processed email IDs from file."""
        try:
            with open(self.filepath, "r") as f:
                self._processed = set(line.strip() for line in f if line.strip())
            logger.debug(f"Loaded {len(self._processed)} processed email IDs")
        except FileNotFoundError:
            logger.debug("No processed emails file found, starting fresh")
            self._processed = set()

    def _save(self) -> None:
        """Save processed email IDs to file."""
        with open(self.filepath, "w") as f:
            f.write("\n".join(sorted(self._processed)))

    def is_processed(self, message_id: str) -> bool:
        """Check if an email has already been processed."""
        return message_id in self._processed

    def mark_processed(self, message_id: str) -> None:
        """Mark an email as processed."""
        self._processed.add(message_id)
        self._save()
        logger.debug(f"Marked email {message_id} as processed")

    def count(self) -> int:
        """Return the number of processed emails."""
        return len(self._processed)
