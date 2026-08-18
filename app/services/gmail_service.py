from pathlib import Path
import base64
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


BASE_DIR = Path(__file__).resolve().parents[2]

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


# READ ONLY - NO EMAILS WILL BE SENT
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def get_gmail_service():

    credentials = None

    if TOKEN_FILE.exists():

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    if not credentials or not credentials.valid:

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):

            credentials.refresh(
                Request()
            )

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

        TOKEN_FILE.write_text(
            credentials.to_json()
        )

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )


def extract_body(payload):

    body_data = (
        payload
        .get("body", {})
        .get("data")
    )

    if body_data:

        return base64.urlsafe_b64decode(
            body_data
        ).decode(
            "utf-8",
            errors="ignore"
        )


    for part in payload.get("parts", []):

        mime_type = part.get(
            "mimeType",
            ""
        )

        if mime_type in [
            "text/plain",
            "text/html"
        ]:

            data = (
                part
                .get("body", {})
                .get("data")
            )

            if data:

                return base64.urlsafe_b64decode(
                    data
                ).decode(
                    "utf-8",
                    errors="ignore"
                )


        if part.get("parts"):

            nested_body = extract_body(part)

            if nested_body:

                return nested_body

    return ""


def fetch_emails(
    max_results=None,
    query=None
):

    service = get_gmail_service()

    message_refs = []

    page_token = None

    while True:

        request = {
            "userId": "me",
            "maxResults": 100
        }

        if page_token:
            request["pageToken"] = page_token

        if query:
            request["q"] = query

        result = (
            service
            .users()
            .messages()
            .list(**request)
            .execute()
        )

        message_refs.extend(
            result.get(
                "messages",
                []
            )
        )

        if (
            max_results
            and len(message_refs) >= max_results
        ):

            message_refs = message_refs[
                :max_results
            ]

            break

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break


    emails = []

    for message_ref in message_refs:

        try:

            email = (
                service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=message_ref["id"],
                    format="full"
                )
                .execute()
            )

            payload = email.get(
                "payload",
                {}
            )

            headers = payload.get(
                "headers",
                []
            )

            subject = ""
            sender = ""
            date = ""

            for header in headers:

                name = header["name"].lower()
                value = header.get(
                    "value",
                    ""
                )

                if name == "subject":
                    subject = value

                elif name == "from":
                    sender = value

                elif name == "date":
                    date = value


            body = extract_body(payload)

            internal_date = int(
                email.get(
                    "internalDate",
                    0
                )
            )

            emails.append(
                {
                    "message_id":
                        message_ref["id"],

                    "thread_id":
                        email.get(
                            "threadId",
                            ""
                        ),

                    "subject":
                        subject,

                    "sender":
                        sender,

                    "date":
                        date,

                    "internal_date":
                        internal_date,

                    "body":
                        body
                }
            )

        except Exception as e:

            print(
                f"Could not fetch email "
                f"{message_ref['id']}: {e}"
            )


    emails.sort(
        key=lambda x: x.get(
            "internal_date",
            0
        ),
        reverse=True
    )

    return emails


def get_email_by_id(
    message_id: str
):

    service = get_gmail_service()

    email = (
        service
        .users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )

    payload = email.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    subject = ""
    sender = ""
    date = ""

    for header in headers:

        name = header["name"].lower()
        value = header.get(
            "value",
            ""
        )

        if name == "subject":
            subject = value

        elif name == "from":
            sender = value

        elif name == "date":
            date = value


    body = extract_body(payload)

    return {
        "message_id":
            message_id,

        "thread_id":
            email.get(
                "threadId",
                ""
            ),

        "subject":
            subject,

        "sender":
            sender,

        "date":
            date,

        "body":
            body
    }


def count_emails_today():

    service = get_gmail_service()

    now = datetime.now().astimezone()

    midnight = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    timestamp = int(
        midnight.timestamp()
    )

    query = f"after:{timestamp}"

    total_count = 0
    page_token = None

    while True:

        request = {
            "userId": "me",
            "maxResults": 500,
            "q": query
        }

        if page_token:
            request["pageToken"] = page_token

        result = (
            service
            .users()
            .messages()
            .list(**request)
            .execute()
        )

        total_count += len(
            result.get(
                "messages",
                []
            )
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return total_count