from __future__ import print_function

import base64
import binascii
import logging
import os.path
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest

from utils.cache import Cache
from utils.config import Config
from utils.db import DatabaseConnector
from utils.logging_utils import ListHandler
from utils.parser import (
    apply_regex,
    clean_html,
    find_matches_from_pattern,
)

# Set up a module-level logger
logger = logging.getLogger(__name__)


class GmailClient:
    def __init__(
        self,
        token_path: str = "token.json",
        token_dict: Optional[Dict[str, Any]] = None,
        creds_dict: Optional[Dict[str, Any]] = None,
    ):
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.creds = self._init_creds(token_path, token_dict, creds_dict)
        self.service = self._open_service()

        # Create a cache of previous API calls to avoid unnecessary calls
        self.api_calls_cache = Cache()

        # Memo to save the corresponding label id for each message id
        self.label_id_to_folder_name_memo: Dict[str, str] = {}
        self.message_id_to_label_id_memo: Dict[str, str] = {}

    def _init_creds(
        self,
        token_path: str,
        token_dict: Optional[Dict[str, Any]],
        creds_dict: Optional[Dict[str, Any]],
    ) -> Optional[Credentials]:
        """Initializes the Gmail client credentials."""
        creds = None
        if token_dict:
            creds = Credentials(
                token_dict["token"],
                refresh_token=token_dict["refresh_token"],
                token_uri=token_dict["token_uri"],
                client_id=token_dict["client_id"],
                client_secret=token_dict["client_secret"],
                scopes=token_dict["scopes"],
                expiry=token_dict["expiry"],
            )
        elif os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.scopes)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing token...")
                creds.refresh(Request())
            else:
                if creds_dict:
                    flow = InstalledAppFlow.from_client_config(creds_dict, self.scopes)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", self.scopes
                    )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds

    def _open_service(self):
        """Opens the Gmail service."""
        return build("gmail", "v1", credentials=self.creds)

    def get_label_id(self, label_name: str) -> Optional[str]:
        """
        Returns the label ID for the given label name.
        """
        cache_key = f"get_label_id_{label_name}"
        cached_id = self.api_calls_cache.get(cache_key)
        if cached_id is not None:
            logger.info(f'Found cached label ID for "{label_name}": "{cached_id}"')
            self.label_id_to_folder_name_memo[cached_id] = label_name
            return cached_id

        logger.info(f'Label "{label_name}" not found in cache. Calling Gmail API...')

        try:
            req = self.service.users().labels().list(userId="me")
            res = req.execute()
        except Exception as e:
            logger.error(f"Error fetching labels: {e}")
            return None

        labels = res.get("labels", [])
        if not labels:
            logger.warning("No labels found.")
            return None

        for label in labels:
            if label["name"] == label_name:
                self.api_calls_cache.set(cache_key, label["id"])
                self.label_id_to_folder_name_memo[label["id"]] = label_name
                return label["id"]

        logger.warning(f'Label "{label_name}" not found.')
        return None

    def get_message_ids(self, label_ids: List[str]) -> List[str]:
        """
        Returns a list of message IDs for the given label IDs.
        """
        all_message_ids = []
        for label_id in label_ids:
            req = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[label_id],
                    includeSpamTrash=False,
                )
            )

            while req:
                try:
                    res = req.execute()
                except Exception as e:
                    logger.error(
                        f"Error fetching message IDs for label {label_id}: {e}"
                    )
                    break

                message_ids = res.get("messages", [])
                message_ids = [message["id"] for message in message_ids]

                for message_id in message_ids:
                    self.message_id_to_label_id_memo[message_id] = label_id

                all_message_ids.extend(message_ids)

                next_page_token = res.get("nextPageToken")
                if not next_page_token:
                    break

                req = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        labelIds=[label_id],
                        pageToken=next_page_token,
                        includeSpamTrash=False,
                    )
                )

        return all_message_ids

    def get_messages_batch(self, message_ids: List[str]) -> Dict[str, Dict]:
        """
        Fetches messages in batch, utilizing cache where possible.
        """
        results = {}
        ids_to_fetch = []

        # Check cache first
        for mid in message_ids:
            cache_key = f"get_message_{mid}"
            cached_msg = self.api_calls_cache.get(cache_key)
            if cached_msg:
                results[mid] = cached_msg
                logger.debug(f'Found cached message for ID "{mid}"')
            else:
                ids_to_fetch.append(mid)

        if not ids_to_fetch:
            return results

        logger.info(
            f"Fetching {len(ids_to_fetch)} messages from Gmail API (batched)..."
        )

        # Helper callback for batch execution
        def batch_callback(request_id, response, exception):
            if exception:
                logger.error(f"Error fetching message {request_id}: {exception}")
            else:
                results[request_id] = response
                self.api_calls_cache.set(f"get_message_{request_id}", response)

        # Batch request
        batch: BatchHttpRequest = self.service.new_batch_http_request(
            callback=batch_callback
        )

        # Add requests to batch
        # Note: The batch 'request_id' must be unique. We use the message ID.
        for mid in ids_to_fetch:
            batch.add(
                self.service.users().messages().get(userId="me", id=mid, format="full"),
                request_id=mid,
            )

        try:
            batch.execute()
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")

        return results


def decode_message_content(message_id: str, message_content: Dict) -> Optional[str]:
    """Extracts and decodes the HTML body from a message dictionary."""
    raw_message_content = None
    payload = message_content.get("payload", {})
    mime_type = payload.get("mimeType")

    if mime_type == "text/html":
        raw_message_content = payload.get("body", {}).get("data")
    elif mime_type == "multipart/alternative":
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/html":
                raw_message_content = part.get("body", {}).get("data")
                if raw_message_content:
                    break

    if not raw_message_content:
        logger.debug(f'Message "{message_id}" does not expose an HTML body; skipping.')
        return None

    try:
        raw_bytes = raw_message_content.encode("ascii")
        padding_needed = (-len(raw_bytes)) % 4
        raw_bytes += b"=" * padding_needed
        return base64.urlsafe_b64decode(raw_bytes).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as err:
        logger.error(f'Failed to decode message "{message_id}" : {err}')
        return None


def process_transactions(
    client: GmailClient,
    cfg: Config,
    messages: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """
    Decodes messages, extracts transaction details, and prepares them for DB insertion.
    """
    transaction_msgs_agg = []
    emails_dir = Path("emails")
    emails_dir.mkdir(parents=True, exist_ok=True)

    for mid, content in messages.items():
        decoded_html = decode_message_content(mid, content)
        if not decoded_html:
            continue

        # Save to file (legacy requirement)
        emails_path = emails_dir / f"message_{mid}.txt"
        ct_cleaned = clean_html(decoded_html)

        try:
            with open(emails_path, "w", encoding="utf-8") as f:
                f.write(ct_cleaned)
        except IOError as e:
            logger.error(f"Failed to write email file for {mid}: {e}")

        ct_trimmed = ct_cleaned.replace("\n", " ")

        # Identify folder and pattern
        label_id = client.message_id_to_label_id_memo.get(mid)
        if not label_id:
            logger.warning(f"Missing label mapping for message {mid}")
            continue

        folder_name = client.label_id_to_folder_name_memo.get(label_id)
        if not folder_name:
            logger.warning(f"Missing folder name mapping for label {label_id}")
            continue

        match_pattern = cfg.get_match_pattern(folder_name)
        use_regex = match_pattern["use_regex"]
        regex_pat = match_pattern["regex"] if use_regex else None

        if use_regex:
            ct_trimmed = apply_regex(ct_trimmed, regex_pat)

        amount = find_matches_from_pattern(
            match_pattern["amount"], ct_trimmed, pat_type="amount", use_regex=use_regex
        )
        date = find_matches_from_pattern(
            match_pattern["date"], ct_trimmed, pat_type="date", use_regex=use_regex
        )
        vendor = find_matches_from_pattern(
            match_pattern["vendor"], ct_trimmed, pat_type="vendor", use_regex=use_regex
        )

        logger.info(f"Extracted - Date: {date}, Amount: {amount}, Vendor: {vendor}")

        transaction_msgs_agg.append(
            {
                "id": mid,
                "folder_name": folder_name,
                "content": ct_cleaned,
                "transaction_date": date,
                "transaction_amount": amount,
                "transaction_vendor": vendor,
            }
        )

    return transaction_msgs_agg


def save_to_database(
    client: GmailClient,
    cfg: Config,
    transactions: List[Dict[str, Any]],
):
    """
    Inserts folders and messages into the database.
    """
    try:
        db = DatabaseConnector(**cfg.get_db_details())
        cursor = db.conn.cursor()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return

    # Ensure folders exist
    folder_name_id_latest_msg_id_memo = {}

    # Use the memo from client to get all relevant folders
    for folder_name in client.label_id_to_folder_name_memo.values():
        try:
            cursor.execute(
                "SELECT * FROM folders WHERE folder_name = %s", (folder_name,)
            )
            result = cursor.fetchone()

            if result is None:
                cursor.execute(
                    """INSERT INTO folders (email_server, folder_name)
                    VALUES (%s, %s) RETURNING id""",
                    ("gmail", folder_name),
                )
                folder_id = cursor.fetchone()[0]
                folder_name_id_latest_msg_id_memo[folder_name] = (folder_id, None)
            else:
                folder_id, _, _, last_trans_date = result
                folder_name_id_latest_msg_id_memo[folder_name] = (
                    folder_id,
                    last_trans_date,
                )
        except Exception as e:
            logger.error(f"Error syncing folder '{folder_name}': {e}")

    # Insert transactions
    for msg in transactions:
        folder_info = folder_name_id_latest_msg_id_memo.get(msg["folder_name"])
        if not folder_info:
            continue

        folder_id, last_trans_date = folder_info

        # Skip if older than last transaction
        if (
            last_trans_date
            and msg["transaction_date"]
            and msg["transaction_date"] <= last_trans_date
        ):
            continue

        # Basic validation
        if not msg["transaction_date"]:
            # logger.debug(f"Skipping message {msg['id']}: No transaction date")
            continue

        try:
            cursor.execute(
                """
                INSERT INTO messages (
                    id, folder_id, content, transaction_date, 
                    transaction_vendor, transaction_amount
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
                """,
                (
                    msg["id"],
                    folder_id,
                    msg["content"],
                    msg["transaction_date"],
                    msg["transaction_vendor"],
                    msg["transaction_amount"],
                ),
            )
        except Exception as e:
            logger.error(f"Error inserting message {msg['id']}: {e}")

    # Update folders with latest transaction date
    try:
        cursor.execute(
            """
            UPDATE folders f
            SET last_trans_date = sub.max_date
            FROM (
                SELECT folder_id, MAX(transaction_date) as max_date
                FROM messages
                GROUP BY folder_id
            ) sub
            WHERE f.id = sub.folder_id;
            """
        )
    except Exception as e:
        logger.error(f"Error updating folder stats: {e}")

    cursor.close()


def main(cfg_dict: Optional[Dict] = None) -> List[str]:
    # Configure logging
    log_capture_list = []
    handler = ListHandler(log_capture_list)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to root logger or module logger
    # We use module logger here but ensure it propagates or we add to root if needed
    # For simplicity, let's configure the root logger to output to stdout as well
    # and our list handler.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if main is called multiple times in same process
    if not any(isinstance(h, ListHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)

        # Also add a stream handler for console output if not present
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

    try:
        # Load config
        cfg = Config(
            config_path="config.json",
            config_dict=cfg_dict["APP_CONFIG"] if cfg_dict else None,
        )

        # Initialize client
        client = GmailClient(
            token_path="token.json",
            token_dict=cfg_dict["GOOGLE_TOKEN"] if cfg_dict else None,
            creds_dict=cfg_dict["GOOGLE_CREDENTIALS"] if cfg_dict else None,
        )

        # Get internal folder IDs
        folders = cfg.get_folders(type="gmail")
        label_ids = []
        for folder in folders:
            label_id = client.get_label_id(folder)
            if label_id:
                label_ids.append(label_id)

        # Get message IDs
        message_ids = client.get_message_ids(label_ids)

        if not message_ids:
            logger.info("No messages found.")
            return log_capture_list

        # Get messages (Batch)
        messages_map = client.get_messages_batch(message_ids)

        # Process transactions
        transactions = process_transactions(client, cfg, messages_map)

        # Save to DB
        save_to_database(client, cfg, transactions)

    except Exception as e:
        logger.error(f"Critical error in main pipeline: {e}", exc_info=True)

    # Clean up handler to prevent memory leaks or duplicate logs in long-running process
    root_logger.removeHandler(handler)

    return log_capture_list


if __name__ == "__main__":
    main()
