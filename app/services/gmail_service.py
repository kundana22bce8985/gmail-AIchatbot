import base64
from datetime import datetime, timezone

import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# =========================================================
# GMAIL PERMISSION
# =========================================================

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

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )

    return service


# =========================================================
# DECODE GMAIL BODY
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
# GET EMAIL HEADER
# =========================================================

def get_header(headers, name):

    for header in headers:

        if header.get(
            "name",
            ""
        ).lower() == name.lower():

            return header.get(
                "value",
                ""
            )

    return ""


# =========================================================
# EXTRACT EMAIL BODY
# =========================================================

def extract_body(payload):

    body = ""

    # -----------------------------------------------------
    # Simple email
    # -----------------------------------------------------

    if payload.get(
        "body",
        {}
    ).get(
        "data"
    ):

        body = decode_body(
            payload["body"]["data"]
        )

    # -----------------------------------------------------
    # Multipart email
    # -----------------------------------------------------

    parts = payload.get(
        "parts",
        []
    )

    for part in parts:

        mime_type = part.get(
            "mimeType",
            ""
        )

        # Plain text
        if mime_type == "text/plain":

            data = (
                part.get(
                    "body",
                    {}
                ).get(
                    "data"
                )
            )

            if data:

                body += (
                    "\n"
                    + decode_body(data)
                )

        # Nested multipart
        elif mime_type.startswith(
            "multipart/"
        ):

            body += (
                "\n"
                + extract_body(part)
            )

    return body.strip()


# =========================================================
# EXTRACT ONE GMAIL MESSAGE
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

        "text": body,

        "internal_date": internal_date
    }


# =========================================================
# GET SINGLE MESSAGE BY ID
# =========================================================
# Kept because your existing streamlit_app.py imports it.
# =========================================================

def get_email_by_id(message_id):

    service = get_gmail_service()

    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )

    return extract_message(
        message
    )


# =========================================================
# GET COMPLETE GMAIL THREAD
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
    # Latest message
    # -----------------------------------------------------

    latest = extracted_messages[-1]

    # -----------------------------------------------------
    # Combine all messages in conversation
    # -----------------------------------------------------

    combined_parts = []

    for message in extracted_messages:

        part = (
            f"From: {message['sender']}\n"
            f"Date: {message['date']}\n"
            f"Subject: {message['subject']}\n\n"
            f"{message['body']}"
        )

        combined_parts.append(
            part
        )

    full_text = (
        "\n\n"
        "--------------------"
        "\n\n"
    ).join(
        combined_parts
    )

    return {

        # IMPORTANT:
        # Thread ID represents one Gmail conversation.

        "message_id": thread_id,

        "thread_id": thread_id,

        "subject": latest[
            "subject"
        ],

        "sender": latest[
            "sender"
        ],

        "date": latest[
            "date"
        ],

        "body": full_text,

        "text": full_text,

        "internal_date": latest[
            "internal_date"
        ],

        # Number of individual messages
        # inside this conversation.

        "message_count": len(
            extracted_messages
        )
    }


# =========================================================
# FETCH GMAIL CONVERSATIONS
# =========================================================
# This returns Gmail THREADS, not individual messages.
#
# If Gmail shows:
#
# 1–6 of 6
#
# this function will return approximately 6 threads.
# =========================================================

def fetch_emails(max_results=100):

    service = get_gmail_service()

    threads = []

    page_token = None

    # -----------------------------------------------------
    # Get maximum 100 Inbox conversations
    # -----------------------------------------------------

    while len(threads) < max_results:

        remaining = (
            max_results
            - len(threads)
        )

        result = (
            service.users()
            .threads()
            .list(
                userId="me",

                # Only Inbox conversations
                labelIds=["INBOX"],

                maxResults=min(
                    100,
                    remaining
                ),

                pageToken=page_token
            )
            .execute()
        )

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
    # Download complete conversations
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
                f"Error reading Gmail "
                f"thread {thread_id}: {e}"
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

        result = (
            service.users()
            .threads()
            .list(
                userId="me",

                labelIds=["INBOX"],

                q=query,

                maxResults=100,

                pageToken=page_token
            )
            .execute()
        )

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
