import streamlit as st

from app.services.gmail_service import (
    fetch_emails,
    get_email_by_id,
    count_emails_today
)

from app.services.content_reader import (
    prepare_email
)

from app.services.vector_store import (
    ingest_emails,
    search_emails
)

from app.services.llm_service import (
    generate_answer,
    summarize_email,
    generate_reply_suggestion
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Gmail AI Agent",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# UI CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #FFFFFF;
        color: #202124;
    }

    section[data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #E5E7EB;
    }

    .app-title {
        color: #1A73E8;
        font-size: 34px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .app-subtitle {
        color: #5F6368;
        font-size: 15px;
        margin-top: 4px;
        margin-bottom: 25px;
    }

    .stButton > button {
        width: 100%;
        background-color: #1A73E8;
        color: white;
        border: none;
        border-radius: 8px;
        height: 42px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: #1557B0;
        color: white;
    }

    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "synced" not in st.session_state:
    st.session_state.synced = False

if "email_count" not in st.session_state:
    st.session_state.email_count = 0

if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

if "selected_email" not in st.session_state:
    st.session_state.selected_email = None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("## 📧 Gmail AI")

    st.caption(
        "Your personal Gmail AI assistant"
    )

    st.divider()

    # -----------------------------------------------------
    # GMAIL SYNC
    # -----------------------------------------------------

    st.markdown("### 📥 Email Database")

    if st.button("🔄 Sync Gmail"):

        with st.spinner(
            "Fetching all Gmail emails..."
        ):

            emails = fetch_emails(
                max_results=100
            )

        with st.spinner(
            "Cleaning emails and building FAISS..."
        ):

            cleaned_emails = [
                prepare_email(email)
                for email in emails
            ]

            chunks = ingest_emails(
                cleaned_emails
            )

        st.session_state.synced = True

        st.session_state.email_count = len(
            emails
        )

        st.session_state.chunk_count = chunks

        st.success(
            f"Synced {len(emails)} emails"
        )

        st.info(
            f"Indexed {chunks} chunks"
        )

    # -----------------------------------------------------
    # DATABASE STATUS
    # -----------------------------------------------------

    if st.session_state.synced:

        st.markdown("### 📊 Database")

        st.write(
            f"📧 Emails: "
            f"**{st.session_state.email_count}**"
        )

        st.write(
            f"🧩 Chunks: "
            f"**{st.session_state.chunk_count}**"
        )

        st.success("FAISS ready")

    else:

        st.warning(
            "Sync Gmail before searching."
        )

    st.divider()

    # -----------------------------------------------------
    # CLEAR CHAT
    # -----------------------------------------------------

    if st.button("🗑️ Clear Chat"):

        st.session_state.messages = []

        st.session_state.selected_email = None

        st.rerun()

    st.divider()

    st.caption(
        "Gmail API • FAISS • RAG • Groq"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="app-title">📧 Gmail AI Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="app-subtitle">'
    'Search, understand and chat with your Gmail using AI'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )

        # Show sources if available

        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):

            with st.expander(
                "📚 View email sources"
            ):

                for i, source in enumerate(
                    message["sources"],
                    1
                ):

                    st.markdown(
                        f"**Source {i}**"
                    )

                    st.write(
                        "**Subject:** "
                        + source.get(
                            "subject",
                            ""
                        )
                    )

                    st.write(
                        "**From:** "
                        + source.get(
                            "sender",
                            ""
                        )
                    )

                    st.write(
                        "**Date:** "
                        + source.get(
                            "date",
                            ""
                        )
                    )

                    st.divider()


# =========================================================
# REQUEST DETECTION
# =========================================================

def is_today_count_request(question):

    q = question.lower().strip()

    patterns = [
        "how many mails did i get today",
        "how many emails did i get today",
        "how many mails today",
        "how many emails today",
        "number of mails today",
        "number of emails today",
        "emails received today",
        "mails received today",
        "how many messages today"
    ]

    return any(
        pattern in q
        for pattern in patterns
    )


def is_full_email_request(question):

    q = question.lower().strip()

    patterns = [
        "give me the full mail",
        "give me the full email",
        "give the full mail",
        "give the full email",
        "show me the full mail",
        "show me the full email",
        "complete mail",
        "complete email",
        "entire mail",
        "entire email",
        "whole mail",
        "whole email"
    ]

    return any(
        pattern in q
        for pattern in patterns
    )


def is_summary_request(question):

    q = question.lower().strip()

    patterns = [
        "summarize this mail",
        "summarize this email",
        "summarize the mail",
        "summarize the email",
        "give me a summary",
        "summary of this mail",
        "summary of this email",
        "what is this mail about"
    ]

    return any(
        pattern in q
        for pattern in patterns
    )


def is_reply_suggestion_request(question):

    q = question.lower().strip()

    patterns = [
        "what should i reply",
        "what should i reply to this mail",
        "what should i reply to this email",
        "what can i reply",
        "how should i reply",
        "how should i respond",
        "suggest a reply",
        "suggest reply",
        "give me a reply",
        "write a reply",
        "draft a reply",
        "reply to this mail",
        "reply to this email"
    ]

    return any(
        pattern in q
        for pattern in patterns
    )


# =========================================================
# CHAT INPUT
# =========================================================

question = st.chat_input(
    "Ask anything about your emails..."
)


if question:

    # =====================================================
    # SAVE USER QUESTION
    # =====================================================

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)


    # =====================================================
    # ASSISTANT RESPONSE
    # =====================================================

    with st.chat_message("assistant"):

        answer = ""

        sources = []


        # =================================================
        # COUNT TODAY'S EMAILS
        # =================================================

        if is_today_count_request(question):

            with st.spinner(
                "📊 Counting today's emails..."
            ):

                count = count_emails_today()

            answer = (
                f"📧 You received "
                f"**{count} emails today**."
            )

            st.markdown(answer)


        else:

            # =================================================
            # CHECK SYNC
            # =================================================

            if not st.session_state.synced:

                answer = (
                    "Please click **🔄 Sync Gmail** "
                    "first."
                )

                st.warning(answer)


            else:

                # =============================================
                # SEARCH EMAILS
                # =============================================

                with st.spinner(
                    "🔎 Searching your emails..."
                ):

                    documents = search_emails(
                        question,
                        k=5
                    )


                # =============================================
                # NO RESULTS
                # =============================================

                if not documents:

                    answer = (
                        "I couldn't find a relevant "
                        "email."
                    )

                    st.info(answer)


                else:

                    # =========================================
                    # GET SELECTED EMAIL
                    # =========================================

                    message_id = (
                        documents[0]
                        .metadata
                        .get(
                            "message_id"
                        )
                    )


                    if message_id:

                        with st.spinner(
                            "📧 Retrieving email..."
                        ):

                            selected_email = (
                                get_email_by_id(
                                    message_id
                                )
                            )

                        st.session_state.selected_email = (
                            selected_email
                        )


                    # =========================================
                    # FULL EMAIL
                    # =========================================

                    if is_full_email_request(
                        question
                    ):

                        email = (
                            st.session_state.selected_email
                        )

                        answer = (
                            f"### 📧 "
                            f"{email['subject']}\n\n"
                            f"**From:** "
                            f"{email['sender']}\n\n"
                            f"**Date:** "
                            f"{email['date']}\n\n"
                            f"---\n\n"
                            f"{email['body']}"
                        )

                        st.markdown(answer)


                        sources = [
                            {
                                "message_id":
                                    email[
                                        "message_id"
                                    ],

                                "subject":
                                    email[
                                        "subject"
                                    ],

                                "sender":
                                    email[
                                        "sender"
                                    ],

                                "date":
                                    email[
                                        "date"
                                    ]
                            }
                        ]


                    # =========================================
                    # SUMMARY
                    # =========================================

                    elif is_summary_request(
                        question
                    ):

                        email = (
                            st.session_state.selected_email
                        )

                        with st.spinner(
                            "📝 Creating summary..."
                        ):

                            summary = summarize_email(
                                email
                            )

                        answer = (
                            "### 📝 Email Summary\n\n"
                            + summary
                        )

                        st.markdown(answer)


                        sources = [
                            {
                                "message_id":
                                    email[
                                        "message_id"
                                    ],

                                "subject":
                                    email[
                                        "subject"
                                    ],

                                "sender":
                                    email[
                                        "sender"
                                    ],

                                "date":
                                    email[
                                        "date"
                                    ]
                            }
                        ]


                    # =========================================
                    # REPLY SUGGESTION
                    # =========================================

                    elif is_reply_suggestion_request(
                        question
                    ):

                        email = (
                            st.session_state.selected_email
                        )

                        with st.spinner(
                            "✍️ Preparing reply suggestion..."
                        ):

                            reply = (
                                generate_reply_suggestion(
                                    email
                                )
                            )

                        answer = (
                            "### 💬 Suggested Reply\n\n"
                            + reply
                        )

                        st.markdown(answer)

                        st.info(
                            "💡 This is only a suggestion. "
                            "Copy it to Gmail and send it "
                            "yourself."
                        )


                        sources = [
                            {
                                "message_id":
                                    email[
                                        "message_id"
                                    ],

                                "subject":
                                    email[
                                        "subject"
                                    ],

                                "sender":
                                    email[
                                        "sender"
                                    ],

                                "date":
                                    email[
                                        "date"
                                    ]
                            }
                        ]


                    # =========================================
                    # NORMAL RAG QUESTION
                    # =========================================

                    else:

                        with st.spinner(
                            "🤖 Generating answer..."
                        ):

                            answer = generate_answer(
                                question,
                                documents,
                                st.session_state.messages
                            )

                        st.markdown(answer)


                        for document in documents:

                            sources.append(
                                {
                                    "message_id":
                                        document.metadata.get(
                                            "message_id",
                                            ""
                                        ),

                                    "subject":
                                        document.metadata.get(
                                            "subject",
                                            ""
                                        ),

                                    "sender":
                                        document.metadata.get(
                                            "sender",
                                            ""
                                        ),

                                    "date":
                                        document.metadata.get(
                                            "date",
                                            ""
                                        )
                                }
                            )


                        if sources:

                            with st.expander(
                                "📚 View email sources"
                            ):

                                for i, source in enumerate(
                                    sources,
                                    1
                                ):

                                    st.markdown(
                                        f"**Source {i}**"
                                    )

                                    st.write(
                                        "**Subject:** "
                                        + source[
                                            "subject"
                                        ]
                                    )

                                    st.write(
                                        "**From:** "
                                        + source[
                                            "sender"
                                        ]
                                    )

                                    st.write(
                                        "**Date:** "
                                        + source[
                                            "date"
                                        ]
                                    )

                                    st.divider()


    # =====================================================
    # SAVE ASSISTANT RESPONSE
    # =====================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources
        }
    )