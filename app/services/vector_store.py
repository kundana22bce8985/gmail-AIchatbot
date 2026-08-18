from pathlib import Path
from datetime import datetime, timezone
import math
import re

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)


BASE_DIR = Path(__file__).resolve().parents[2]

VECTOR_DIR = (
    BASE_DIR
    / "data"
    / "faiss_index"
)


# --------------------------------------------------
# Embedding model
# --------------------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# Text splitter
# --------------------------------------------------

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)


# --------------------------------------------------
# Create FAISS index
# --------------------------------------------------

def ingest_emails(emails: list[dict]) -> int:

    documents = []

    for email in emails:

        text = email.get(
            "text",
            ""
        )

        if not text:
            continue

        chunks = text_splitter.split_text(
            text
        )

        for chunk in chunks:

            documents.append(
                Document(
                    page_content=chunk,

                    metadata={
                        "message_id": email.get(
                            "message_id",
                            ""
                        ),

                        "subject": email.get(
                            "subject",
                            ""
                        ),

                        "sender": email.get(
                            "sender",
                            ""
                        ),

                        "date": email.get(
                            "date",
                            ""
                        ),

                        "internal_date": email.get(
                            "internal_date",
                            0
                        )
                    }
                )
            )

    if not documents:
        return 0

    vector_store = FAISS.from_documents(
        documents,
        embeddings
    )

    VECTOR_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    vector_store.save_local(
        str(VECTOR_DIR)
    )

    return len(documents)


# --------------------------------------------------
# Load FAISS
# --------------------------------------------------

def load_vector_store():

    if not VECTOR_DIR.exists():
        return None

    return FAISS.load_local(
        str(VECTOR_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )


# --------------------------------------------------
# Detect recent-related queries
# --------------------------------------------------

def is_recent_query(query: str) -> bool:

    query = query.lower()

    recent_words = [
        "recent",
        "latest",
        "newest",
        "new",
        "today",
        "yesterday",
        "this week",
        "this month",
        "last week",
        "last month"
    ]

    return any(
        word in query
        for word in recent_words
    )


# --------------------------------------------------
# Recency score
# --------------------------------------------------

def calculate_recency_score(
    internal_date: int
) -> float:

    if not internal_date:
        return 0.0

    try:

        email_time = datetime.fromtimestamp(
            internal_date / 1000,
            tz=timezone.utc
        )

        now = datetime.now(
            timezone.utc
        )

        age_days = max(
            0,
            (
                now - email_time
            ).total_seconds() / 86400
        )

        # Newer emails get a higher score.
        # Score approaches 1 for very recent emails.
        score = math.exp(
            -age_days / 30
        )

        return score

    except Exception:
        return 0.0


# --------------------------------------------------
# Search + Recency Re-ranking
# --------------------------------------------------

def search_emails(
    query: str,
    k: int = 5
):

    vector_store = load_vector_store()

    if vector_store is None:
        return []

    # Get more candidates first.
    candidate_count = max(
        k * 5,
        25
    )

    results = (
        vector_store
        .similarity_search_with_relevance_scores(
            query,
            k=candidate_count
        )
    )

    ranked_results = []

    recent_query = is_recent_query(
        query
    )

    for document, semantic_score in results:

        internal_date = document.metadata.get(
            "internal_date",
            0
        )

        recency_score = calculate_recency_score(
            internal_date
        )

        if recent_query:

            # Recent queries:
            # 70% semantic relevance
            # 30% recency
            final_score = (
                0.70 * semantic_score
                +
                0.30 * recency_score
            )

        else:

            # Normal queries:
            # semantic similarity is more important
            final_score = (
                0.85 * semantic_score
                +
                0.15 * recency_score
            )

        ranked_results.append(
            (
                document,
                final_score
            )
        )

    ranked_results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return [
        document
        for document, score
        in ranked_results[:k]
    ]