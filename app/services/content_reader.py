import re

from bs4 import BeautifulSoup


def clean_email_text(text: str) -> str:

    if not text:

        return ""

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    text = soup.get_text(
        separator=" "
    )

    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def prepare_email(email: dict):

    subject = clean_email_text(
        email.get("subject", "")
    )

    sender = clean_email_text(
        email.get("sender", "")
    )

    body = clean_email_text(
        email.get("body", "")
    )

    date = email.get(
        "date",
        ""
    )

    internal_date = email.get(
        "internal_date",
        0
    )

    combined_text = f"""
Subject: {subject}

From: {sender}

Date: {date}

Email:
{body}
""".strip()

    return {
        "message_id": email.get(
            "message_id",
            ""
        ),

        "thread_id": email.get(
            "thread_id",
            ""
        ),

        "subject": subject,

        "sender": sender,

        "date": date,

        "internal_date": internal_date,

        "text": combined_text
    }