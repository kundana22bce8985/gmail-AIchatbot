from fastapi import APIRouter, HTTPException

from app.services.gmail_service import fetch_emails


router = APIRouter()


@router.get("/emails/read")
def read_emails(limit: int = 20):
    """Read recent emails from Gmail."""

    try:
        emails = fetch_emails(max_results=limit)

        return {
            "count": len(emails),
            "emails": emails
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read emails: {str(e)}"
        )