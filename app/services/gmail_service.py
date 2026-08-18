import base64
from datetime import datetime, timezone

import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


# =========================================================
# GET GMAIL SERVICE
# =========================================================

def get_gmail_service():

    if not st.user.is_logged_in:
        raise RuntimeError(
            "Please login with Google first."
        )

    if "access" not in st.user.tokens:
        raise RuntimeError(
            "Google access token is not available. "
            "Please login again."
        )

    access_token = st.user.tokens["access"]

    credentials = Credentials(
        token=access_token,
        scopes=SCOPES
    )

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )


# =========================================================
# DECODE BODY
# =========================================================

def decode_body(data):

    if not data:
        return ""

    try:
        decoded = base64.urlsafe_b64decode(
            data.encode("UTF-8")
        )

        return decoded.decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:
        return ""


# =========================================================
# GET HEADER
# =========================================================

def get_header(headers, name):

    for header in headers:

        if header.get("name", "").lower() == name.lower():

            return header.get(
                "value",
                ""
            )

    return ""


# =========================================================
# EXTRACT BODY
# =========================================================

def extract_body(payload):

    body = ""

    # Simple email
    if payload.get("body", {}).get("data"):

        body = decode_body(
            payload["body"]["data"]
        )

    # Multipart email
    parts = payload.get(
        "parts",
        []
    )

    for part in parts:

        mime_type = part.get(
            "mimeType",
            ""
        )

        if mime_type == "text/plain":

            data = (
                part.get("body", {})
                .get("data")
            )

            if data:

                body += "\n" + decode_body(
                    data
                )

        elif mime_type.startswith(
            "multipart/"
        ):

            body += "\n" + extract_body(
                part
            )

    return body.strip()


# =========================================================
# EXTRACT ONE MESSAGE
# =========================================================

def extract_message(message):

    payload = message.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    subject = get_header(
        headers,
        "Subject"
    )

    sender = get_header(
        headers,
        "From"
    )

    date = get_header(
        headers,
        "Date"
    )

    body = extract_body(
        payload
    )

    internal_date = int(
        message.get(
            "internalDate",
            0
        )
    )

    return {
        "message_id": message.get(
            "id",
            ""
        ),

        "subject": subject,

        "sender": sender,

        "date": date,

        "body": body,

        "internal_date": internal_date
    }


# =========================================================
# GET ONE THREAD
# =========================================================

def get_thread_by_id(thread_id):

    service = get_gmail_service()

    thread = (
        service.users()
        .threads()
        .get(
            userId="me",
            id=thread_id,
            format="full"
        )
        .execute()
    )

    messages = thread.get(
        "messages",
        []
    )

    if not messages:
        return None

    extracted_messages = []

    for message in messages:

        extracted_messages.append(
            extract_message(message)
        )

    # -----------------------------------------------------
    # Use the latest message as the main metadata
    # -----------------------------------------------------

    latest = extracted_messages[-1]

    # -----------------------------------------------------
    # Combine complete thread content
    # -----------------------------------------------------

    combined_text = []

    for message in extracted_messages:

        combined_text.append(
            f"From: {message['sender']}\n"
            f"Date: {message['date']}\n"
            f"Subject: {message['subject']}\n\n"
            f"{message['body']}"
        )

    full_text = "\n\n--------------------\n\n".join(
        combined_text
    )

    return {
        # Thread ID is used as the unique email/conversation ID
        "message_id": thread_id,

        "thread_id": thread_id,

        "subject": latest["subject"],

        "sender": latest["sender"],

        "date": latest["date"],

        "body": full_text,

        "text": full_text,

        "internal_date": latest["internal_date"],

        # Number of individual messages inside conversation
        "message_count": len(
            extracted_messages
        )
    }


# =========================================================
# FETCH LATEST INBOX CONVERSATIONS
# =========================================================

def fetch_emails(max_results=100):

    service = get_gmail_service()

    threads = []

    page_token = None

    # -----------------------------------------------------
    # Get Gmail conversation/thread IDs
    # -----------------------------------------------------

    while len(threads) < max_results:

        remaining = (
            max_results - len(threads)
        )

        request = (
            service.users()
            .threads()
            .list(
                userId="me",

                # Only Inbox conversations
                labelIds=["INBOX"],

                # Maximum 100 conversations
                maxResults=min(
                    100,
                    remaining
                ),

                pageToken=page_token
            )
        )

        result = request.execute()

        batch = result.get(
            "threads",
            []
        )

        if not batch:
            break

        threads.extend(
            batch
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    # -----------------------------------------------------
    # Remove duplicate thread IDs
    # -----------------------------------------------------

    unique_thread_ids = []

    seen_ids = set()

    for thread in threads:

        thread_id = thread.get(
            "id"
        )

        if not thread_id:
            continue

        if thread_id in seen_ids:
            continue

        seen_ids.add(
            thread_id
        )

        unique_thread_ids.append(
            thread_id
        )

    # -----------------------------------------------------
    # Get complete thread contents
    # -----------------------------------------------------

    emails = []

    for thread_id in unique_thread_ids:

        if len(emails) >= max_results:
            break

        try:

            email = get_thread_by_id(
                thread_id
            )

            if email:

                emails.append(
                    email
                )

        except Exception as e:

            print(
                f"Error reading thread "
                f"{thread_id}: {e}"
            )

    return emails


# =========================================================
# COUNT TODAY'S INBOX CONVERSATIONS
# =========================================================

def count_emails_today():

    service = get_gmail_service()

    today = datetime.now(
        timezone.utc
    ).strftime(
        "%Y/%m/%d"
    )

    query = f"after:{today}"

    count = 0

    page_token = None

    while True:

        request = (
            service.users()
            .threads()
            .list(
                userId="me",

                labelIds=["INBOX"],

                q=query,

                maxResults=100,

                pageToken=page_token
            )
        )

        result = request.execute()

        count += len(
            result.get(
                "threads",
                []
            )
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return count
