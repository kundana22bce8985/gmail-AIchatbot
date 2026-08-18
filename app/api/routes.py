from fastapi import APIRouter

from app.services.gmail_service import fetch_emails
from app.services.content_reader import prepare_email
from app.services.vector_store import ingest_emails


router = APIRouter()


@router.get("/emails")
def get_emails(limit: int = 20):
    """Fetch emails from Gmail."""

    emails = fetch_emails(max_results=limit)

    return {
        "count": len(emails),
        "emails": emails
    }


@router.post("/sync")
def sync_emails():
    """Fetch, clean, and store emails in FAISS."""

    emails = fetch_emails(max_results=100)

    cleaned_emails = [
        prepare_email(email)
        for email in emails
    ]

    chunks = ingest_emails(cleaned_emails)

    return {
        "emails_synced": len(cleaned_emails),
        "chunks_indexed": chunks,
        "message": "Emails successfully indexed in FAISS"
    }