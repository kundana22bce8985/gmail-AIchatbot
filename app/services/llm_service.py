from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings


llm = ChatGroq(
    groq_api_key=settings.groq_api_key,
    model="openai/gpt-oss-20b",
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

    return response.content


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
        body=email.get(
            "body",
            ""
        )
    )

    response = llm.invoke(messages)

    return response.content


# =========================================================
# REPLY SUGGESTION
# =========================================================

def generate_reply_suggestion(
    email,
    instruction=""
):

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

Email:
{body}

User instruction:
{instruction}

Write a natural and professional reply.

Rules:

- Do not invent facts.
- Do not claim that the user completed
  an action unless the user says so.
- Keep the reply appropriate to the email.
- If the email is a job/interview email,
  use a professional tone.
- If the email asks for information that
  the user has not provided, politely ask
  for clarification instead.
- Return ONLY the suggested reply.
- Do not include Subject or To.

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
        body=email.get(
            "body",
            ""
        ),
        instruction=instruction
    )

    response = llm.invoke(messages)

    return response.content