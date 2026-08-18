from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings


# =========================================================
# GROQ LLM
# =========================================================

llm = ChatGroq(
    groq_api_key=settings.groq_api_key,
    model="openai/gpt-oss-20b",
    temperature=0
)


# =========================================================
# HELPER
# =========================================================

def get_response_text(response):

    content = response.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):

        text = ""

        for item in content:

            if isinstance(item, dict):

                if item.get("type") == "text":
                    text += item.get("text", "")

                elif "text" in item:
                    text += item.get("text", "")

            elif isinstance(item, str):
                text += item

        return text.strip()

    return str(content).strip()


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

    answer = get_response_text(response)

    if not answer:

        return (
            "I couldn't generate an answer "
            "from the available email information."
        )

    return answer


# =========================================================
# EMAIL SUMMARY
# =========================================================

def summarize_email(email):

    body = email.get("body", "").strip()

    if not body:

        return (
            "I couldn't find the body text "
            "of this email to summarize it."
        )

    prompt = ChatPromptTemplate.from_template(
"""
You are an email assistant.

Summarize the following email.

Include:

1. Main purpose
2. Important points
3. Dates or deadlines
4. Action required from the user

Keep the summary short and easy to understand.

Subject:
{subject}

From:
{sender}

Date:
{date}

Email:
{body}

Return only the summary.
"""
    )

    messages = prompt.format_messages(
        subject=email.get("subject", ""),
        sender=email.get("sender", ""),
        date=email.get("date", ""),
        body=body
    )

    response = llm.invoke(messages)

    answer = get_response_text(response)

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

    body = email.get("body", "").strip()

    if not body:

        return (
            "I couldn't find the body text "
            "of this email, so I can't draft a reply."
        )


    prompt = ChatPromptTemplate.from_template(
"""
You are an email assistant.

The user wants to write a reply to the email below.

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

Write a natural, short and professional reply.

Rules:

- Base the reply only on the email content.
- Do not invent facts.
- Do not say that the user completed
  something unless it is known.
- If the email is about a job or interview,
  use a professional tone.
- If the sender asks for information that
  the user has not provided, politely ask
  for clarification.
- Do not include a subject line.
- Do not include "Suggested Reply".
- Return ONLY the reply text.

Reply:
"""
    )


    messages = prompt.format_messages(
        subject=email.get("subject", ""),
        sender=email.get("sender", ""),
        date=email.get("date", ""),
        body=body,
        instruction=instruction
    )


    response = llm.invoke(messages)

    answer = get_response_text(response)


    if not answer:

        return (
            "I couldn't generate a reply "
            "for this email."
        )


    return answer
