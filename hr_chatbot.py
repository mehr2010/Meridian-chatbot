
"""
Meridian Logistics HR Assistant
AI DataYard - Module 2, Lab 4

Google Gemini + Streamlit
Fictional HR policies for demonstration purposes.

All chatbot responses are displayed as structured JSON.
"""

import json
import os
import re

import streamlit as st
from google import genai


# ============================================================
# 1. SETTINGS
# ============================================================

POLICY_VERSION = "2026.1"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ============================================================
# 2. APPROVED HR POLICIES
# ============================================================

POLICY = {
    "1.1": (
        "Annual leave: 20 paid days per calendar year, "
        "accrued monthly."
    ),
    "1.2": (
        "Carry forward: Up to 5 unused annual leave days "
        "carry into the next year; the rest lapse on 31 March."
    ),
    "1.3": (
        "Leave notice: 1 to 5 days require 3 working days' "
        "notice. More than 5 consecutive days require "
        "14 days' notice. All annual leave needs "
        "line manager approval."
    ),
    "2.1": (
        "Sick leave: 10 paid days per year. "
        "A medical certificate is required for absences "
        "of 2 or more consecutive days."
    ),
    "3.1": (
        "Working hours: 9:00 to 18:00, Monday to Friday, "
        "with a 15-minute grace period."
    ),
    "3.2": (
        "Remote work: Up to 2 days per week with line "
        "manager approval. Additional days need HR approval."
    ),
    "4.1": (
        "Health insurance: Covers the employee, spouse "
        "and up to 2 children."
    ),
    "5.1": (
        "Confidentiality: HR does not disclose other "
        "employees' pay or personal data."
    ),
}


# ============================================================
# 3. KEYWORD MATCHING
# ============================================================

KEYWORDS = {
    "1.1": [
        "annual leave",
        "leave days",
        "paid leave",
        "paid leaves",
        "vacation",
        "leave entitlement",
    ],
    "1.2": [
        "carry",
        "unused leave",
        "lapse",
    ],
    "1.3": [
        "notice",
        "days off",
        "take leave",
        "time off",
        "consecutive days",
    ],
    "2.1": [
        "sick",
        "medical certificate",
        "doctor note",
        "doctor's note",
    ],
    "3.1": [
        "working hours",
        "start time",
        "grace period",
    ],
    "3.2": [
        "work from home",
        "remote",
        "wfh",
    ],
    "4.1": [
        "insurance",
        "parents",
        "spouse",
        "children",
    ],
    "5.1": [
        "salary",
        "colleague pay",
        "personal data",
    ],
}


FIELDS = (
    "answer",
    "policy_section",
    "answer_found",
    "needs_human",
    "escalation_reason",
)


SENSITIVE = [
    "unfair",
    "harass",
    "complain",
    "complaint",
    "grievance",
    "fired",
    "terminat",
    "pay dispute",
    "pay cut",
    "my manager",
    "leave balance",
    "remaining leave",
    "my balance",
    "colleague",
    "coworker",
    "co-worker",
    "another employee",
    "someone else",
    "my salary",
    "medical records",
]


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def make_response(
    answer,
    policy_section="",
    answer_found=False,
    needs_human=False,
    escalation_reason=""
):
    """
    Create a consistent JSON-compatible dictionary.
    """

    return {
        "answer": answer,
        "policy_section": policy_section,
        "answer_found": answer_found,
        "needs_human": needs_human,
        "escalation_reason": escalation_reason,
    }


def pick_sections(question):
    """
    Find policy sections matching the employee question.
    """

    q = question.lower()

    return [
        sid
        for sid, words in KEYWORDS.items()
        if any(word in q for word in words)
    ]


def requires_hr(question):
    """
    Detect sensitive requests requiring human HR review.
    """

    q = question.lower()

    return any(
        term in q
        for term in SENSITIVE
    )


def format_json(data):
    """
    Convert response dictionary into formatted JSON.
    """

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 5. BUILD GEMINI PROMPT
# ============================================================

def build_prompt(question, ids):
    policy_text = "\n".join(
        f"{sid}: {POLICY[sid]}"
        for sid in ids
    )

    return f"""
You are the HR assistant for fictional Meridian Logistics.

POLICY VERSION:
{POLICY_VERSION}

APPROVED HR POLICY:
{policy_text}

EMPLOYEE QUESTION:
{question}

INSTRUCTIONS:

1. Answer only using the supplied HR policy.
2. Use no more than three sentences.
3. Cite the supporting policy section.
4. Never invent policy information.
5. Never guess numbers, dates or company rules.
6. Escalate complaints, disputes, private employee
   information and questions requiring system lookups.
7. If the policy does not answer the question,
   set answer_found to false and needs_human to true.

Return ONLY valid JSON with exactly these five fields:

{{
    "answer": "string",
    "policy_section": "string",
    "answer_found": true,
    "needs_human": false,
    "escalation_reason": "string"
}}

Use true and false as JSON Boolean values.

If the question is answered, include the policy section.

If the question cannot be answered, use an empty
policy_section and explain the escalation reason.

Do not include Markdown or code fences.
"""


# ============================================================
# 6. GEMINI API KEY
# ============================================================

def get_key():
    """
    Read the API key securely from Streamlit Secrets
    or environment variables.
    """

    try:
        key = st.secrets.get("GEMINI_API_KEY", "")

        if key and str(key).strip():
            return str(key).strip()

    except Exception:
        pass

    return (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or None
    )


# ============================================================
# 7. CALL GOOGLE GEMINI
# ============================================================

def call_model(prompt):
    api_key = get_key()

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0,
        },
    )

    if not response.text:
        raise ValueError(
            "Gemini returned an empty response"
        )

    return response.text


# ============================================================
# 8. VALIDATE GEMINI RESPONSE
# ============================================================

def validate(question, raw, allowed):
    """
    Validate:
    - JSON structure
    - Required fields
    - Policy section citations
    - Numbers against approved policy
    - Sensitive requests
    """

    # Parse JSON.
    try:
        text = raw.strip()

        text = re.sub(
            r"^```(?:json)?",
            "",
            text
        ).strip()

        text = re.sub(
            r"```$",
            "",
            text
        ).strip()

        data = json.loads(text)

    except (ValueError, TypeError):
        return None, "Invalid JSON"

    # Check structure.
    if not isinstance(data, dict):
        return None, "Incorrect JSON structure"

    if set(data.keys()) != set(FIELDS):
        return None, "Incorrect JSON fields"

    # Check data types.
    for field in (
        "answer",
        "policy_section",
        "escalation_reason"
    ):
        if not isinstance(data[field], str):
            return None, "Incorrect JSON field types"

    for field in (
        "answer_found",
        "needs_human"
    ):
        if type(data[field]) is not bool:
            return None, "Incorrect JSON field types"

    # Validate policy sections.
    if data["answer_found"]:
        cited = re.findall(
            r"\b\d+\.\d+\b",
            data["policy_section"]
        )

        if not cited:
            return None, "Missing policy section"

        if any(
            section not in allowed
            for section in cited
        ):
            return None, "Unsupported policy section"

        # Validate numbers.
        supported_text = (
            question
            + " "
            + " ".join(POLICY[s] for s in cited)
        )

        supported_numbers = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            supported_text
        )

        answer_numbers = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            data["answer"]
        )

        if any(
            number not in supported_numbers
            for number in answer_numbers
        ):
            return None, "Unsupported number in answer"

    else:
        data["needs_human"] = True

        if not data["escalation_reason"]:
            data["escalation_reason"] = (
                "The approved HR policy does not "
                "answer this question."
            )

    # Sensitive requests require human review.
    if requires_hr(question):
        data["needs_human"] = True

        if not data["escalation_reason"]:
            data["escalation_reason"] = (
                "Human HR review required."
            )

    return data, None


# ============================================================
# 9. DIRECT ANNUAL LEAVE ANSWER
# ============================================================

def known_leave_answer(question, ids):
    """
    Return the required JSON response for straightforward
    annual leave entitlement questions.
    """

    q = question.lower()

    if "1.1" not in ids:
        return None

    if requires_hr(question):
        return None

    excluded_terms = [
        "sick",
        "carry",
        "notice",
        "remaining",
        "balance",
        "request",
        "approve",
    ]

    if any(term in q for term in excluded_terms):
        return None

    entitlement_terms = [
        "how many",
        "number of",
        "entitled",
        "entitlement",
    ]

    if any(term in q for term in entitlement_terms):
        return make_response(
            answer="You get 20 paid days per year.",
            policy_section="1.1",
            answer_found=True,
            needs_human=False,
            escalation_reason=""
        )

    return None


# ============================================================
# 10. COMPLETE HR QUESTION WORKFLOW
# ============================================================

def answer_question(question):
    """
    1. Identify matching policies.
    2. Check sensitive requests.
    3. Answer known annual leave questions.
    4. Ask Gemini for other policy questions.
    5. Validate JSON.
    6. Retry once if necessary.
    """

    ids = pick_sections(question)

    # Sensitive question.
    if requires_hr(question):
        return make_response(
            answer="This request needs review by HR.",
            policy_section="",
            answer_found=False,
            needs_human=True,
            escalation_reason=(
                "This is a sensitive or personal HR request."
            )
        ), None

    # No matching policy.
    if not ids:
        return make_response(
            answer=(
                "The available policy does not "
                "cover this question."
            ),
            policy_section="",
            answer_found=False,
            needs_human=True,
            escalation_reason=(
                "No matching approved policy section."
            )
        ), None

    # Direct annual leave answer.
    direct = known_leave_answer(question, ids)

    if direct is not None:
        return direct, None

    # Other questions go to Gemini.
    prompt = build_prompt(question, ids)

    problem = "No response"

    for attempt in range(2):
        try:
            if attempt == 0:
                raw = call_model(prompt)
            else:
                raw = call_model(
                    prompt
                    + "\nReturn valid JSON with "
                    + "correct policy citations."
                )

        except Exception as error:
            return None, (
                "Gemini API error: "
                f"{type(error).__name__}"
            )

        data, problem = validate(
            question,
            raw,
            ids
        )

        if problem is None:
            return data, None

    return None, (
        "Gemini response validation failed: "
        + problem
    )


# ============================================================
# 11. HR ESCALATION QUEUE
# ============================================================

def hr_message(question, data):
    """
    Create a demonstration HR queue message.
    """

    return (
        f"Employee question: {question}\n"
        f"Escalation reason: "
        f"{data['escalation_reason']}\n"
        f"Policy section: "
        f"{data['policy_section'] or 'None'}"
    )


# ============================================================
# 12. STREAMLIT APPLICATION
# ============================================================

def main():
    st.set_page_config(
        page_title="Meridian HR Assistant",
        page_icon="💬"
    )

    st.title("Meridian HR Assistant")

    st.caption(
        "Fictional company. Answers come only from "
        f"policy version {POLICY_VERSION}."
    )

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    if not get_key():
        st.error("Gemini API key not detected.")

        st.info(
            "Open your app's Streamlit Community Cloud "
            "Settings → Secrets and add GEMINI_API_KEY. "
            "Save and reboot the application."
        )

        st.stop()

    # --------------------------------------------------------
    # INITIALIZE SESSION STATE
    # --------------------------------------------------------

    if "chat" not in st.session_state:
        st.session_state.chat = []

    if "queue" not in st.session_state:
        st.session_state.queue = []

    if "last" not in st.session_state:
        st.session_state.last = None

    # --------------------------------------------------------
    # DISPLAY CHAT HISTORY AS JSON
    # --------------------------------------------------------

    for role, message in st.session_state.chat:
        with st.chat_message(role):
            if role == "assistant":
                st.code(
                    format_json(message),
                    language="json"
                )
            else:
                st.write(message)

    # --------------------------------------------------------
    # EMPLOYEE QUESTION
    # --------------------------------------------------------

    question = st.chat_input("Ask an HR question")

    if question:
        st.session_state.chat.append(
            ("user", question)
        )

        with st.chat_message("user"):
            st.write(question)

        # Process employee question.
        with st.spinner("Checking approved HR policy..."):
            data, problem = answer_question(question)

        # ----------------------------------------------------
        # HANDLE TECHNICAL ERRORS
        # ----------------------------------------------------

        if problem:
            data = make_response(
                answer=(
                    "I could not complete the policy check "
                    "due to a technical issue. "
                    "Please try again."
                ),
                policy_section="",
                answer_found=False,
                needs_human=False,
                escalation_reason=""
            )

            st.error(problem)

        elif data is not None:
            # Add genuine HR escalations to demonstration queue.
            if data["needs_human"]:
                st.session_state.queue.append(
                    hr_message(question, data)
                )

        else:
            data = make_response(
                answer="No response was available.",
                policy_section="",
                answer_found=False,
                needs_human=False,
                escalation_reason=""
            )

        # Save structured response.
        st.session_state.last = data

        st.session_state.chat.append(
            ("assistant", data)
        )

        # ----------------------------------------------------
        # DISPLAY ALL FIVE JSON FIELDS
        # ----------------------------------------------------

        with st.chat_message("assistant"):
            st.code(
                format_json(data),
                language="json"
            )

    # --------------------------------------------------------
    # HR ESCALATION SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:
        st.header("HR Queue")

        st.caption(
            "Demonstration only. No messages are "
            "sent to a real HR department."
        )

        if not st.session_state.queue:
            st.write("Nothing escalated yet.")

        for message in st.session_state.queue:
            st.code(message, language=None)

        with st.expander("Last structured answer"):
            st.json(st.session_state.last or {})


# ============================================================
# 13. START APPLICATION
# ============================================================

if __name__ == "__main__":
    main()


