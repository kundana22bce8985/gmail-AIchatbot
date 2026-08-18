from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings


# =========================================================
# GROQ LLM
# =========================================================

llm = ChatGroq(
    groq_api_key=settings.groq_api_key,
    model="llama-3.3-70b-versatile",
    temperature=0
)


# =========================================================
# NORMAL RAG ANSWER
# =========================================================

normal_prompt = ChatPromptTemplate.from_template(
"""
You are a Gmail AI assistant.

Answer the user's question using only
the email context below.

Do not invent information.

If the answer is not available,
say that you could not find it.

Use conversation history for follow-up questions.

Conversation history:

{history}

Email context:

{context}

Question:

{question}

Answer:
"""
)


def generate_answer(
    question,
    documents,
    chat_history=None
):

    context_parts = []

    for document in documents:

        context_parts.append(
            f"""
Subject:
{document.metadata.get("subject", "")}

From:
{document.metadata.get("sender", "")}

Date:
{document.metadata.get("date", "")}

Email:
{document.page_content}
"""
        )

    context = "\n\n----------------\n\n".join(
        context_parts
    )

    history = ""

    if chat_history:

        for message in chat_history[-8:]:

            history += (
                f"{message['role']}: "
                f"{message['content']}\n"
            )

    messages = normal_prompt.format_messages(
        history=history,
        context=context,
        question=question
    )

    response = llm.invoke(messages)

    answer = response.content

    if not answer:
        return "I couldn't generate an answer from the available email information."

    return answer


# =========================================================
# EMAIL SUMMARY
# =========================================================

def summarize_email(email):

    prompt = ChatPromptTemplate.from_template(
"""
You are an email assistant.

Summarize the following email.

Include:

1. Main purpose
2. Important points
3. Dates/deadlines
4. Action required from the user

Keep it short and easy to understand.

Subject:
{subject}

From:
{sender}

Date:
{date}

Email:
{body}

Summary:
"""
    )

    body = email.get(
        "body",
        ""
    ).strip()

    if not body:

        return (
            "I couldn't find the body text "
            "of this email to summarize it."
        )

    messages = prompt.format_messages(
        subject=email.get(
            "subject",
            ""
        ),
        sender=email.get(
            "sender",
            ""
        ),
        date=email.get(
            "date",
            ""
        ),
        body=body
    )

    response = llm.invoke(messages)

    answer = response.content

    if not answer:

        return (
            "I couldn't generate a summary "
            "for this email."
        )

    return answer


# =========================================================
# REPLY SUGGESTION
# =========================================================

def generate_reply_suggestion(
    email,
    instruction=""
):

    body = email.get(
        "body",
        ""
    ).strip()

    # -----------------------------------------------------
    # Check whether email body exists
    # -----------------------------------------------------

    if not body:

        return (
            "I couldn't find the body text "
            "of this email, so I can't draft "
            "a reply."
        )


    prompt = ChatPromptTemplate.from_template(
"""
You are an email assistant.

The user wants to know what they should
reply to this email.

Original email:

Subject:
{subject}

From:
{sender}

Date:
{date}

Email:
{body}

User instruction:
{instruction}

Write a natural and professional reply.

Rules:

- Write the reply based only on the email.
- Do not invent facts.
- Do not claim that the user completed
  an action unless the email or user
  instruction says so.
- Keep the reply appropriate to the email.
- If the email is a job or interview email,
  use a professional tone.
- If the email asks for information that
  the user has not provided, politely ask
  for clarification.
- Keep the reply concise.
- Do not include a subject line.
- Do not include "Suggested Reply:".
- Return ONLY the email reply.

Suggested reply:
"""
    )


    messages = prompt.format_messages(
        subject=email.get(
            "subject",
            ""
        ),
        sender=email.get(
            "sender",
            ""
        ),
        date=email.get(
            "date",
            ""
        ),
        body=body,
        instruction=instruction
    )


    response = llm.invoke(
        messages
    )


    answer = response.content


    # -----------------------------------------------------
    # Safety check
    # -----------------------------------------------------

    if not answer:

        return (
            "I couldn't generate a reply "
            "for this email."
        )


    return answer.strip()
