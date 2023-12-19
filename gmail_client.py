from __future__ import print_function

import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from utils.config import Config
from utils.cache import Cache
from utils.db import DatabaseConnector
from utils.parser import *


class GmailClient:
    def __init__(self, token_path="token.json"):
        self.creds = None
        self.service = None
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

        self.creds = self._init_creds(token_path)
        self.service = self._open_service()

        # Create a cache of previous API calls to avoid unnecessary calls
        self.api_calls_cache = Cache()

        # Memo to save the corresponding label id for each message id
        self.label_id_to_folder_name_memo = {}
        self.message_id_to_label_id_memo = {}

    def _init_creds(self, token_path):
        """
        Initializes the Gmail client.
        """
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(
                token_path, self.scopes
            )

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing token...")
                creds.refresh(Request())
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
        """
        Opens the Gmail service.
        """
        return build("gmail", "v1", credentials=self.creds)

    def get_label_id(self, label_name):
        """
        Returns the label ID for the given label name.
        Args:
            label_name (str): The name of the label.
        Returns:
            str: The label ID.
        """
        # Check if label ID is cached
        cache_key = f"get_label_id_{label_name}"
        cached_id = self.api_calls_cache.get(cache_key)
        if cached_id is not None:
            print(f'Found cached label ID for "{label_name}": "{cached_id}"')
            self.label_id_to_folder_name_memo[cached_id] = label_name
            return cached_id

        print(f'Label "{label_name}" not found in cache. Calling Gmail API...')
        req = self.service.users().labels().list(userId="me")
        res = req.execute()

        labels = res.get("labels", [])
        if not labels:
            print("No labels found.")
            return None

        for label in labels:
            if label["name"] == label_name:
                self.api_calls_cache.set(cache_key, label["id"])
                self.label_id_to_folder_name_memo[label["id"]] = label_name
                return label["id"]

        print(f'Label "{label_name}" not found.')
        return None

    def get_message_ids(self, label_ids):
        """
        Returns a list of message IDs for the given label IDs.
        Args:
            label_ids (list): A list of label IDs.
        Returns:
            list: A list of message IDs.
        """
        all_message_ids = []
        for label_id in label_ids:
            # Check if messages are cached
            cache_key = f"get_message_ids_{label_id}"
            cached_messages = self.api_calls_cache.get(cache_key)
            if cached_messages is None:
                print(
                    f"Message IDs for label ID {label_id} not found in cache. Calling Gmail API..."
                )
                req = (
                    self.service.users()
                    .messages()
                    .list(userId="me", labelIds=[label_id])
                )
                res = req.execute()

                message_ids = res.get("messages", [])
                message_ids = [message["id"] for message in message_ids]

                self.api_calls_cache.set(cache_key, message_ids)

            else:
                print(f"Found cached message IDs for label ID {label_id}")
                message_ids = cached_messages

            for message_id in message_ids:
                self.message_id_to_label_id_memo[message_id] = label_id

            all_message_ids.extend(message_ids)

        return all_message_ids

    def get_message(self, message_id):
        """
        Returns a message for the given message ID.
        Args:
            message_id (str): The message ID.
        Returns:
            dict: The message.
        """
        # Check if message is cached
        cache_key = f"get_message_{message_id}"
        cached_message = self.api_calls_cache.get(cache_key)
        if cached_message is not None:
            print(f'Found cached message for ID "{message_id}"')
            return cached_message

        print(
            f'Message for ID "{message_id}" not found in cache. Calling Gmail API...'
        )
        req = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
        )
        res = req.execute()

        self.api_calls_cache.set(cache_key, res)

        return res


if __name__ == "__main__":
    # Load config with the desired email clients and folders
    cfg = Config("config.json")
    cfg.print()

    # Initialize client to use Gmail API
    client = GmailClient()

    # Get internal folder IDs for each folder
    folders = cfg.get_folders(type="gmail")
    label_ids = []
    for folder in folders:
        label_id = client.get_label_id(folder)
        if label_id is not None:
            label_ids.append(label_id)

    # Get message IDs for each folder
    message_ids = client.get_message_ids(label_ids)

    # Get message for each message ID
    message_contents = []
    for message_id in message_ids:
        message = client.get_message(message_id)
        message_contents.append((message_id, message))

    # Get the raw message content for each message
    raw_message_contents = []
    for message_id, message_content in message_contents:
        if message_content["payload"]["mimeType"] == "text/html":
            raw_message_content = message_content["payload"]["body"]["data"]
        elif message_content["payload"]["mimeType"] == "multipart/alternative":
            for part in message_content["payload"]["parts"]:
                if part["mimeType"] == "text/html":
                    raw_message_content = part["body"]["data"]
                    break
        raw_message_contents.append((message_id, raw_message_content))

    # Decode the raw messages from base64
    decoded_message_contents = []
    for message_id, raw_message_content in raw_message_contents:
        decoded_message_content = base64.urlsafe_b64decode(
            raw_message_content
        ).decode("utf-8")
        decoded_message_contents.append((message_id, decoded_message_content))

    # Create text files for each message
    transaction_msgs_agg = []
    for i, ct in decoded_message_contents:
        # Create emails directory if it doesn't exist
        if not os.path.exists("emails"):
            os.makedirs("emails")

        # Clean up the emails in a readable format - TODO: probably remove soon
        ct_cleaned = clean_html(ct)
        with open(f"emails/message_{i}.txt", "w") as stripped_f:
            stripped_f.write(ct_cleaned)
        ct_trimmed = ct_cleaned.replace("\n", " ")

        # Retrieve the transaction details from the email, namely the date,
        # amount, and vendor
        # First, retrieve the credit card folder name for the email to do the
        # appropriate pattern lookup
        label_id = client.message_id_to_label_id_memo[i]
        folder_name = client.label_id_to_folder_name_memo[label_id]

        # Retrieve the correct match pattern for the credit card folder name
        match_pattern = cfg.get_match_pattern(folder_name)
        amount_pat = match_pattern["amount"]
        date_pat = match_pattern["date"]
        vendor_pat = match_pattern["vendor"]

        # Find the transaction attributes within the email using the patterns
        amount = find_matches_from_pattern(
            amount_pat, ct_trimmed, pat_type="amount"
        )
        date = find_matches_from_pattern(date_pat, ct_trimmed, pat_type="date")
        vendor = find_matches_from_pattern(
            vendor_pat, ct_trimmed, pat_type="vendor"
        )
        print(f"Date: {date}, Amount: {amount}, Vendor: {vendor}")

        # Store the aggregated message object for database processing
        message_agg = {
            "id": i,
            "folder_name": folder_name,
            "content": ct_cleaned,
            "transaction_date": date,
            "transaction_amount": amount,
            "transaction_vendor": vendor,
        }
        transaction_msgs_agg.append(message_agg)

    # Connect to the database
    db = DatabaseConnector(**cfg.get_db_details())
    cursor = db.conn.cursor()

    # Create a row for each folder if it does not exist in the database
    folder_name_id_latest_msg_id_memo = {}
    for folder_name in client.label_id_to_folder_name_memo.values():
        cursor.execute(
            """SELECT * FROM folders WHERE folder_name = (%s)""", (folder_name,)
        )
        result1 = cursor.fetchone()
        if result1 is None:
            cursor.execute(
                """INSERT INTO folders (email_server, folder_name)
                VALUES (%s, %s) RETURNING id;""",
                ("gmail", folder_name),
            )
            folder_id = cursor.fetchone()[0]

            # Populate the lookup dict for the folder names to their ids
            folder_name_id_latest_msg_id_memo[folder_name] = (
                folder_id,
                None,
            )
        else:
            folder_id, _, folder_name, last_trans_date = result1
            folder_name_id_latest_msg_id_memo[folder_name] = (
                folder_id,
                last_trans_date,
            )

    # Insert the new transactions - we want to insert only the messages with
    # transaction dates occurring after the latest transactions in the database
    for msg in transaction_msgs_agg:
        folder_id, last_trans_date = folder_name_id_latest_msg_id_memo[
            msg["folder_name"]
        ]

        # Skip loading messages that are already loaded in the database
        if last_trans_date and msg["transaction_date"] <= last_trans_date:
            continue

        query = """
        INSERT INTO messages (
            id,
            folder_id,
            content,
            transaction_date,
            transaction_vendor,
            transaction_amount
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(
            query,
            (
                msg["id"],
                folder_id,
                msg["content"],
                msg["transaction_date"],
                msg["transaction_vendor"],
                msg["transaction_amount"],
            ),
        )

    # Retrieve the last transaction date for the uploaded messages
    cursor.execute(
        """
        SELECT DISTINCT transaction_date, folder_id FROM messages 
        WHERE (folder_id, transaction_date) IN (
            SELECT folder_id, MAX(transaction_date) FROM messages
            GROUP BY folder_id
            ORDER BY folder_id
        );"""
    )
    latest_loads_by_folder = cursor.fetchall()

    # For each folder, update the last transaction date to the latest date of
    # the imported messages
    for res in latest_loads_by_folder:
        query = """
            UPDATE folders
            SET last_trans_date = (%s)
            WHERE id = (%s);
        """
        cursor.execute(query, (res[0], res[1]))
