import base64
from datetime import datetime, timezone

import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


# =========================================================
# GET GMAIL SERVICE USING LOGGED-IN GOOGLE USER
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
# GET HEADER
# =========================================================

def get_header(headers, name):

    for header in headers:

        if header["name"].lower() == name.lower():

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

            data = part.get(
                "body",
                {}
            ).get(
                "data"
            )

            if data:

                body += "\n" + decode_body(
                    data
                )

        elif mime_type.startswith(
            "multipart/"
        ):

            body += extract_body(
                part
            )

    return body.strip()


# =========================================================
# GET SINGLE EMAIL
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

    return {
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "date": date,
        "body": body
    }


# =========================================================
# FETCH EMAILS
# =========================================================

def fetch_emails(max_results=100):

    service = get_gmail_service()

    messages = []

    page_token = None

    while len(messages) < max_results:

        remaining = (
            max_results - len(messages)
        )

        request = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=min(
                    100,
                    remaining
                ),
                pageToken=page_token
            )
        )

        result = request.execute()

        batch = result.get(
            "messages",
            []
        )

        if not batch:
            break

        messages.extend(
            batch
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    emails = []

    for message in messages[:max_results]:

        try:

            email = get_email_by_id(
                message["id"]
            )

            emails.append(
                email
            )

        except Exception as e:

            print(
                f"Error reading email "
                f"{message.get('id')}: {e}"
            )

    return emails


# =========================================================
# COUNT TODAY'S EMAILS
# =========================================================

def count_emails_today():

    service = get_gmail_service()

    today = datetime.now(
        timezone.utc
    ).strftime(
        "%Y/%m/%d"
    )

    query = f"after:{today}"

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=query
        )
        .execute()
    )

    count = len(
        result.get(
            "messages",
            []
        )
    )

    page_token = result.get(
        "nextPageToken"
    )

    while page_token:

        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                pageToken=page_token
            )
            .execute()
        )

        count += len(
            result.get(
                "messages",
                []
            )
        )

        page_token = result.get(
            "nextPageToken"
        )

    return count
