import streamlit as st


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
# GOOGLE LOGIN
# =========================================================

if not st.user.is_logged_in:

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:120px;
        ">
            <h1>📧 Gmail AI Agent</h1>
            <p>
                Search, understand and chat with your Gmail
                using AI.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        st.button(
            "🔐 Login with Google",
            on_click=st.login,
            use_container_width=True
        )

    st.stop()


# =========================================================
# IMPORT SERVICES
# =========================================================

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
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #FFFFFF;
    }

    section[data-testid="stSidebar"] {
        background-color: #F8F9FA;
    }

    .app-title {
        color: #1A73E8;
        font-size: 34px;
        font-weight: 700;
    }

    .app-subtitle {
        color: #5F6368;
        font-size: 15px;
        margin-bottom: 25px;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
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

    st.markdown(
        "## 📧 Gmail AI"
    )

    st.caption(
        f"Logged in as "
        f"{st.user.get('email', '')}"
    )

    st.divider()

    # -----------------------------------------------------
    # SYNC
    # -----------------------------------------------------

    st.markdown(
        "### 📥 Email Database"
    )

    if st.button(
        "🔄 Sync Gmail",
        use_container_width=True
    ):

        with st.spinner(
            "Fetching latest 100 emails..."
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
    # STATUS
    # -----------------------------------------------------

    if st.session_state.synced:

        st.markdown(
            "### 📊 Database"
        )

        st.write(
            f"📧 Emails: "
            f"**{st.session_state.email_count}**"
        )

        st.write(
            f"🧩 Chunks: "
            f"**{st.session_state.chunk_count}**"
        )

        st.success(
            "FAISS ready"
        )

    else:

        st.warning(
            "Click Sync Gmail first."
        )


    st.divider()


    # -----------------------------------------------------
    # CLEAR CHAT
    # -----------------------------------------------------

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.session_state.selected_email = None

        st.rerun()


    # -----------------------------------------------------
    # LOGOUT
    # -----------------------------------------------------

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.logout()


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
# REQUEST DETECTION
# =========================================================

def is_today_count_request(question):

    q = question.lower()

    patterns = [
        "how many mails did i get today",
        "how many emails did i get today",
        "how many mails today",
        "how many emails today",
        "number of mails today",
        "number of emails today",
        "emails received today",
        "mails received today"
    ]

    return any(
        x in q
        for x in patterns
    )


def is_full_email_request(question):

    q = question.lower()

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
        "entire email"
    ]

    return any(
        x in q
        for x in patterns
    )


def is_summary_request(question):

    q = question.lower()

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
        x in q
        for x in patterns
    )


def is_reply_request(question):

    q = question.lower()

    patterns = [
        "what should i reply",
        "what should i reply to this mail",
        "what should i reply to this email",
        "what can i reply",
        "how should i reply",
        "how should i respond",
        "suggest a reply",
        "give me a reply",
        "write a reply",
        "draft a reply"
    ]

    return any(
        x in q
        for x in patterns
    )


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

question = st.chat_input(
    "Ask anything about your emails..."
)


if question:

    # -----------------------------------------------------
    # USER MESSAGE
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)


    # -----------------------------------------------------
    # ASSISTANT
    # -----------------------------------------------------

    with st.chat_message("assistant"):

        answer = ""


        # =================================================
        # TODAY COUNT
        # =================================================

        if is_today_count_request(
            question
        ):

            with st.spinner(
                "Counting today's emails..."
            ):

                count = count_emails_today()

            answer = (
                f"📧 You received "
                f"**{count} emails today**."
            )

            st.markdown(answer)


        # =================================================
        # CHECK SYNC
        # =================================================

        elif not st.session_state.synced:

            answer = (
                "Please click **🔄 Sync Gmail** "
                "first so I can search your emails."
            )

            st.warning(answer)


        else:

            # =============================================
            # RAG SEARCH
            # =============================================

            with st.spinner(
                "🔎 Searching your emails..."
            ):

                documents = search_emails(
                    question,
                    k=5
                )


            if not documents:

                answer = (
                    "I couldn't find a relevant "
                    "email."
                )

                st.info(answer)


            else:

                # =========================================
                # GET EMAIL
                # =========================================

                message_id = (
                    documents[0]
                    .metadata
                    .get(
                        "message_id"
                    )
                )

                email = None

                if message_id:

                    try:

                        email = get_email_by_id(
                            message_id
                        )

                        st.session_state.selected_email = (
                            email
                        )

                    except Exception:

                        email = None


                # =========================================
                # FULL EMAIL
                # =========================================

                if (
                    is_full_email_request(question)
                    and email
                ):

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


                # =========================================
                # SUMMARY
                # =========================================

                elif (
                    is_summary_request(question)
                    and email
                ):

                    with st.spinner(
                        "📝 Creating summary..."
                    ):

                        answer = summarize_email(
                            email
                        )

                    st.markdown(
                        "### 📝 Email Summary"
                    )

                    st.markdown(answer)


                # =========================================
                # REPLY SUGGESTION
                # =========================================

                elif (
                    is_reply_request(question)
                    and email
                ):

                    with st.spinner(
                        "✍️ Preparing reply suggestion..."
                    ):

                        answer = (
                            generate_reply_suggestion(
                                email
                            )
                        )

                    st.markdown(
                        "### 💬 Suggested Reply"
                    )

                    st.markdown(answer)

                    st.info(
                        "This is only a suggestion. "
                        "Copy it to Gmail and send it "
                        "yourself."
                    )


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


    # =====================================================
    # SAVE RESPONSE
    # =====================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
