from pathlib import Path
from datetime import datetime, timezone
import math

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

VECTOR_DIR = (
    BASE_DIR
    / "data"
    / "faiss_index"
)


# =========================================================
# EMBEDDING MODEL
# =========================================================

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# =========================================================
# TEXT SPLITTER
# =========================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)


# =========================================================
# CREATE / SAVE FAISS INDEX
# =========================================================

def ingest_emails(emails: list[dict]) -> int:

    documents = []

    for email in emails:

        text = email.get(
            "text",
            ""
        )

        # Fallback to body
        if not text:

            text = email.get(
                "body",
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

                        # Thread ID / message ID
                        "message_id": email.get(
                            "message_id",
                            ""
                        ),

                        "thread_id": email.get(
                            "thread_id",
                            email.get(
                                "message_id",
                                ""
                            )
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
                        ),

                        "message_count": email.get(
                            "message_count",
                            1
                        )
                    }
                )
            )

    # No documents
    if not documents:
        return 0

    # -----------------------------------------------------
    # Create FAISS index
    # -----------------------------------------------------

    vector_store = FAISS.from_documents(
        documents,
        embeddings
    )

    # -----------------------------------------------------
    # Create directory
    # -----------------------------------------------------

    VECTOR_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Save index
    # -----------------------------------------------------

    vector_store.save_local(
        str(VECTOR_DIR)
    )

    # Return number of chunks
    return len(documents)


# =========================================================
# LOAD FAISS INDEX
# =========================================================

def load_vector_store():

    if not VECTOR_DIR.exists():

        return None

    try:

        return FAISS.load_local(
            str(VECTOR_DIR),
            embeddings,
            allow_dangerous_deserialization=True
        )

    except Exception as e:

        print(
            f"Error loading FAISS index: {e}"
        )

        return None


# =========================================================
# DETECT RECENT-RELATED QUERIES
# =========================================================

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


# =========================================================
# RECENCY SCORE
# =========================================================

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

        # Newer emails get higher scores
        score = math.exp(
            -age_days / 30
        )

        return score

    except Exception:

        return 0.0


# =========================================================
# SEARCH EMAILS
# =========================================================
#
# IMPORTANT:
# k = 10 means return up to 10 UNIQUE emails.
#
# One email may have multiple chunks.
# We rank chunks first, then keep only one result
# for each email/thread.
# =========================================================

def search_emails(
    query: str,
    k: int = 10
):

    vector_store = load_vector_store()

    if vector_store is None:

        return []

    # -----------------------------------------------------
    # Number of candidates
    # -----------------------------------------------------

    candidate_count = max(
        k * 5,
        50
    )

    # Prevent requesting more documents than exist
    try:

        total_documents = vector_store.index.ntotal

        candidate_count = min(
            candidate_count,
            total_documents
        )

    except Exception:

        pass

    if candidate_count <= 0:

        return []

    # -----------------------------------------------------
    # Semantic search
    # -----------------------------------------------------

    results = (
        vector_store
        .similarity_search_with_relevance_scores(
            query,
            k=candidate_count
        )
    )

    if not results:

        return []

    # -----------------------------------------------------
    # Check whether query is recent-related
    # -----------------------------------------------------

    recent_query = is_recent_query(
        query
    )

    ranked_results = []

    # -----------------------------------------------------
    # Rank every chunk
    # -----------------------------------------------------

    for document, semantic_score in results:

        internal_date = document.metadata.get(
            "internal_date",
            0
        )

        recency_score = calculate_recency_score(
            internal_date
        )

        # -------------------------------------------------
        # Recent queries
        # -------------------------------------------------

        if recent_query:

            final_score = (
                0.70 * semantic_score
                +
                0.30 * recency_score
            )

        # -------------------------------------------------
        # Normal queries
        # -------------------------------------------------

        else:

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

    # -----------------------------------------------------
    # Sort highest score first
    # -----------------------------------------------------

    ranked_results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    # =====================================================
    # REMOVE DUPLICATE EMAILS
    # =====================================================
    #
    # Example:
    #
    # Email A → chunk 1
    # Email A → chunk 2
    # Email A → chunk 3
    #
    # We return Email A only once.
    # =====================================================

    unique_results = []

    seen_email_ids = set()

    for document, score in ranked_results:

        email_id = document.metadata.get(
            "thread_id",
            document.metadata.get(
                "message_id",
                ""
            )
        )

        # If no ID exists, use a fallback
        if not email_id:

            email_id = (
                document.metadata.get(
                    "subject",
                    ""
                )
                + "|"
                + document.metadata.get(
                    "sender",
                    ""
                )
            )

        # Skip duplicate email
        if email_id in seen_email_ids:

            continue

        seen_email_ids.add(
            email_id
        )

        unique_results.append(
            document
        )

        # -------------------------------------------------
        # Stop after k UNIQUE emails
        # -------------------------------------------------

        if len(unique_results) >= k:

            break

    return unique_results
