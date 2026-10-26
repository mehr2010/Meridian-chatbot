"""
Meridian Logistics HR Assistant
AI DataYard - Module 2, Lab 4

Google Gemini + Streamlit
Fictional HR policy chatbot.

All answers use five-field JSON.
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
# 3. RESPONSE STRUCTURE
# ============================================================

FIELDS = (
    "answer",
    "policy_section",
    "answer_found",
    "needs_human",
    "escalation_reason",
)


def make_response(
    answer,
    policy_section="",
    answer_found=False,
    needs_human=False,
    escalation_reason=""
):
    return {
        "answer": answer,
        "policy_section": policy_section,
        "answer_found": answer_found,
        "needs_human": needs_human,
        "escalation_reason": escalation_reason,
    }


def format_json(data):
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 4. QUESTION NORMALIZATION AND MATCHING
# ============================================================

def normalize(question):
    text = question.lower().strip()
    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text


KEYWORDS = {
    "1.1": [
        "annual leave",
        "paid leave",
        "paid leaves",
        "vacation",
        "leave entitlement",
        "leave days",
    ],
    "1.2": [
        "carry forward",
        "carry over",
        "unused leave",
        "lapse",
    ],
    "1.3": [
        "leave notice",
        "notice period",
        "days off",
        "take leave",
        "time off",
    ],
    "2.1": [
        "sick",
        "medical certificate",
        "doctor's note",
        "doctor note",
    ],
    "3.1": [
        "working hours",
        "office hours",
        "start time",
        "grace period",
    ],
    "3.2": [
        "work from home",
        "working from home",
        "remote",
        "wfh",
    ],
    "4.1": [
        "insurance",
        "health coverage",
        "medical coverage",
    ],
    "5.1": [
        "confidentiality",
        "personal data",
        "another employee's pay",
    ],
}


def pick_sections(question):
    q = normalize(question)

    matched = [
        section
        for section, words in KEYWORDS.items()
        if any(word in q for word in words)
    ]

    return matched


# ============================================================
# 5. HUMAN HR REVIEW
# ============================================================

SENSITIVE = [
    "harass",
    "grievance",
    "complaint",
    "unfair treatment",
    "pay dispute",
    "pay cut",
    "my salary",
    "leave balance",
    "remaining leave",
    "my balance",
    "my manager",
    "termination",
    "fired",
    "medical records",
    "another employee",
    "colleague's salary",
]


def requires_hr(question):
    q = normalize(question)

    return any(
        term in q
        for term in SENSITIVE
    )


# ============================================================
# 6. TOPIC-SPECIFIC POLICY ANSWERS
# ============================================================

def maternity_answer():
    return make_response(
        answer=(
            "I could not find a maternity leave policy "
            "in the HR policy provided to me, so I can't "
            "give you details. I'd recommend contacting "
            "HR directly for accurate information on "
            "maternity leave."
        ),
        policy_section="",
        answer_found=False,
        needs_human=True,
        escalation_reason=(
            f"The provided policy (version {POLICY_VERSION}) "
            "has no section on maternity leave, so the "
            "question must be answered by HR."
        )
    )


def annual_leave_answer():
    return make_response(
        answer=(
            "You get 20 paid annual leave days per "
            "calendar year, accrued monthly."
        ),
        policy_section="1.1",
        answer_found=True,
        needs_human=False,
        escalation_reason=""
    )


def remote_work_answer(days=None):
    if days is not None and days > 2:
        if days == 3:
            answer = (
                "You can work from home up to 2 days per "
                "week with your line manager's approval. "
                "A third day would need additional approval "
                "from HR, so please contact HR if you'd "
                "like to request it."
            )
            reason = (
                "Working 3 days a week remotely exceeds "
                "the 2-day limit and requires HR approval "
                "under section 3.2."
            )
        else:
            answer = (
                "You can work from home up to 2 days per "
                "week with your line manager's approval. "
                "Additional days require HR approval, "
                "so please contact HR about your request."
            )
            reason = (
                f"Working {days} days a week remotely "
                "exceeds the 2-day limit and requires "
                "HR approval under section 3.2."
            )

        return make_response(
            answer=answer,
            policy_section="3.2",
            answer_found=True,
            needs_human=True,
            escalation_reason=reason
        )

    return make_response(
        answer=(
            "You can work from home up to 2 days per "
            "week with your line manager's approval. "
            "Additional days require HR approval."
        ),
        policy_section="3.2",
        answer_found=True,
        needs_human=False,
        escalation_reason=""
    )


def sick_leave_answer(question):
    q = normalize(question)

    match = re.search(
        r"\b(\d+)\s+(?:consecutive\s+)?days?\b",
        q
    )

    if match:
        days = int(match.group(1))

        if days >= 2:
            return make_response(
                answer=(
                    f"Yes. For an absence of {days} "
                    "consecutive days, you must provide "
                    "a medical certificate."
                ),
                policy_section="2.1",
                answer_found=True,
                needs_human=False,
                escalation_reason=""
            )

        return make_response(
            answer=(
                "The policy requires a medical certificate "
                "for absences of 2 or more consecutive days. "
                "A one-day absence does not meet that "
                "certificate requirement."
            ),
            policy_section="2.1",
            answer_found=True,
            needs_human=False,
            escalation_reason=""
        )

    return make_response(
        answer=(
            "Employees receive 10 paid sick leave days "
            "per year. A medical certificate is required "
            "for absences of 2 or more consecutive days."
        ),
        policy_section="2.1",
        answer_found=True,
        needs_human=False,
        escalation_reason=""
    )


# ============================================================
# 7. DIRECT POLICY ANSWER ROUTER
# ============================================================

def direct_answer(question, ids):
    q = normalize(question)

    # Missing maternity policy.
    if "maternity" in q:
        return maternity_answer()

    # Sensitive personal requests.
    if requires_hr(question):
        return make_response(
            answer=(
                "This request needs review by HR. "
                "Please contact the HR department "
                "for appropriate assistance."
            ),
            policy_section="",
            answer_found=False,
            needs_human=True,
            escalation_reason=(
                "This is a sensitive or personal HR request."
            )
        )

    # Annual leave entitlement.
    annual_terms = [
        "how many",
        "entitled",
        "entitlement",
        "number of",
    ]

    if (
        "1.1" in ids
        and len(ids) == 1
        and any(term in q for term in annual_terms)
    ):
        return annual_leave_answer()

    # Remote work.
    if "3.2" in ids and len(ids) == 1:
        match = re.search(
            r"\b(\d+)\s+days?\b",
            q
        )

        if match:
            days = int(match.group(1))
            return remote_work_answer(days)

        if any(
            term in q
            for term in [
                "how many",
                "allowed",
                "policy",
                "can i work",
            ]
        ):
            return remote_work_answer()

    # Sick leave / medical certificate.
    if "2.1" in ids and len(ids) == 1:
        if any(
            term in q
            for term in [
                "doctor",
                "certificate",
                "how many",
                "sick leave",
            ]
        ):
            return sick_leave_answer(question)

    return None


# ============================================================
# 8. GEMINI API KEY
# ============================================================

def get_key():
    try:
        key = st.secrets.get(
            "GEMINI_API_KEY",
            ""
        )

        if key and str(key).strip():
            return str(key).strip()

    except Exception:
        pass

    return (
        os.environ.get(
            "GEMINI_API_KEY",
            ""
        ).strip()
        or None
    )


# ============================================================
# 9. BUILD GROUNDED GEMINI PROMPT
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

You must answer only using the approved HR policy.

DECISION RULES:

1. If the policy answers the question completely:
   answer_found = true
   needs_human = false

2. If the policy answers the question but additional
   HR approval or intervention is required:
   answer_found = true
   needs_human = true

3. If the policy does not answer the question:
   answer_found = false
   needs_human = true

4. If answer_found is true, cite the supporting
   policy section.

5. If needs_human is true, explain the specific
   reason in escalation_reason.

6. Use clear, natural, professional HR wording.

7. Do not invent leave entitlements, company rules,
   approval requirements, or other policy information.

8. Never claim to have checked employee records.

9. Do not disclose private employee information.

10. Return exactly five JSON fields.

EXPECTED JSON STRUCTURE:

{{
    "answer": "string",
    "policy_section": "string",
    "answer_found": true,
    "needs_human": false,
    "escalation_reason": "string"
}}

Return only JSON.
Do not include Markdown or code fences.
"""


# ============================================================
# 10. CALL GEMINI
# ============================================================

def call_model(prompt):
    api_key = get_key()

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing"
        )

    client = genai.Client(
        api_key=api_key
    )

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
# 11. VALIDATE GEMINI JSON
# ============================================================

def validate(question, raw, allowed):
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

    if not isinstance(data, dict):
        return None, "Incorrect JSON structure"

    if set(data.keys()) != set(FIELDS):
        return None, "Incorrect JSON fields"

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

        supported_text = (
            question + " "
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

        if not data["answer"].strip():
            return None, "Empty answer"

    else:
        data["policy_section"] = ""
        data["needs_human"] = True

        if not data["escalation_reason"].strip():
            data["escalation_reason"] = (
                "The approved policy does not "
                "answer this question."
            )

    if data["needs_human"]:
        if not data["escalation_reason"].strip():
            return None, "Missing escalation reason"

    else:
        data["escalation_reason"] = ""

    return data, None


# ============================================================
# 12. MISSING POLICY RESPONSE
# ============================================================

def missing_policy_answer(question):
    q = normalize(question)

    # Specific maternity wording.
    if "maternity" in q:
        return maternity_answer()

    # Generic response for other unsupported topics.
    return make_response(
        answer=(
            "I could not find information about your "
            "question in the approved HR policy provided "
            "to me. Please contact HR for accurate details."
        ),
        policy_section="",
        answer_found=False,
        needs_human=True,
        escalation_reason=(
            f"The approved policy (version {POLICY_VERSION}) "
            "does not contain information that answers "
            "this question, so HR review is required."
        )
    )


# ============================================================
# 13. COMPLETE QUESTION WORKFLOW
# ============================================================

def answer_question(question):
    ids = pick_sections(question)

    # First check deterministic policy answers.
    direct = direct_answer(question, ids)

    if direct is not None:
        return direct, None

    # Missing policy: do not invent an answer.
    if not ids:
        return missing_policy_answer(question), None

    # Ask Gemini for other supported topics.
    prompt = build_prompt(question, ids)

    problem = "No response"

    for attempt in range(2):
        try:
            retry_prompt = prompt

            if attempt == 1:
                retry_prompt += (
                    "\nEnsure your response uses "
                    "exactly five JSON fields and "
                    "correct policy citations."
                )

            raw = call_model(retry_prompt)

        except Exception as error:
            return None, (
                "Gemini API error: "
                f"{type(error).__name__}. "
                "Check the Streamlit Cloud logs."
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
# 14. HR ESCALATION QUEUE
# ============================================================

def hr_message(question, data):
    return (
        f"Employee question: {question}\n"
        f"Escalation reason: "
        f"{data['escalation_reason']}\n"
        f"Policy section: "
        f"{data['policy_section'] or 'None'}"
    )


# ============================================================
# 15. STREAMLIT APPLICATION
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

    # Initialize session state.
    if "chat" not in st.session_state:
        st.session_state.chat = []

    if "queue" not in st.session_state:
        st.session_state.queue = []

    if "last" not in st.session_state:
        st.session_state.last = None

    # Display chat history.
    for role, message in st.session_state.chat:
        with st.chat_message(role):
            if role == "assistant":
                st.code(
                    format_json(message),
                    language="json"
                )
            else:
                st.write(message)

    # Employee question input.
    question = st.chat_input(
        "Ask an HR question"
    )

    if question:
        st.session_state.chat.append(
            ("user", question)
        )

        with st.chat_message("user"):
            st.write(question)

        # Process question.
        with st.spinner(
            "Checking approved HR policy..."
        ):
            data, problem = answer_question(question)

        # Technical errors are separate from HR cases.
        if problem:
            data = make_response(
                answer=(
                    "I could not complete the policy check "
                    "because of a technical issue. "
                    "Please try again."
                ),
                policy_section="",
                answer_found=False,
                needs_human=False,
                escalation_reason=""
            )

            st.error(problem)

        elif data is not None:
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

        # Display JSON.
        with st.chat_message("assistant"):
            st.code(
                format_json(data),
                language="json"
            )

    # Sidebar.
    with st.sidebar:
        st.header("HR Queue")

        st.caption(
            "Demonstration only. No messages are "
            "sent to a real HR department."
        )

        if not st.session_state.queue:
            st.write("Nothing escalated yet.")

        for message in st.session_state.queue:
            st.code(
                message,
                language=None
            )

        with st.expander("Last structured answer"):
            st.json(
                st.session_state.last or {}
            )

        if st.button("Clear chat history"):
            st.session_state.chat = []
            st.session_state.queue = []
            st.session_state.last = None
            st.rerun()


# ============================================================
# 16. START APPLICATION
# ============================================================

if __name__ == "__main__":
    main()

