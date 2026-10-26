"""Meridian HR chatbot: Google Gemini + Streamlit.

AI DataYard - AI Automation Bootcamp - Module 2
Fictional company and fictional data only.

Deployment:
1. Upload this file and requirements.txt to GitHub.
2. Deploy the repository on Streamlit Community Cloud.
3. Add GEMINI_API_KEY to Streamlit Secrets.
4. Never put your real API key in this file.
"""

import json
import os
import re

import streamlit as st
from google import genai


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

POLICY_VERSION = "2026.1"

MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)


# ------------------------------------------------------------
# HR POLICY
# ------------------------------------------------------------

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
        "Leave notice: 1 to 5 days: 3 working days' notice. "
        "More than 5 consecutive days: 14 days' notice. "
        "All annual leave needs line manager approval."
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


# ------------------------------------------------------------
# STEP 1: PICK RELEVANT POLICY SECTIONS
# ------------------------------------------------------------

KEYWORDS = {
    "1.1": ["annual leave", "leave days", "vacation"],
    "1.2": ["carry", "lapse", "unused leave"],
    "1.3": ["notice", "days off", "take leave", "time off"],
    "2.1": ["sick", "doctor", "medical certificate"],
    "3.1": ["working hours", "start time", "grace"],
    "3.2": ["work from home", "remote", "wfh"],
    "4.1": ["insurance", "cover my parents"],
    "5.1": ["salary", "pay", "personal data"],
}


def pick_sections(question):
    q = question.lower()

    return [
        sid
        for sid, words in KEYWORDS.items()
        if any(word in q for word in words)
    ]


# ------------------------------------------------------------
# TODO 1: GROUNDED HR PROMPT
# ------------------------------------------------------------

PROMPT_TEMPLATE = """
You are an expert HR assistant at Meridian Logistics.

POLICY VERSION:
{{policy_version}}

APPROVED HR POLICY:
{{policy_text}}

EMPLOYEE QUESTION:
{{question}}

INSTRUCTIONS:

1. Answer ONLY using the approved HR policy above.

2. Find the policy section that answers the question.

3. Answer in plain language using three sentences or fewer.

4. Include the supporting policy section.

5. If the policy does not clearly answer the question:
   - Set answer_found to false.
   - Set needs_human to true.
   - Explain why escalation is needed.

ALWAYS ESCALATE:
- Complaints about managers or colleagues.
- Harassment, grievances or pay disputes.
- Termination and sensitive medical details.
- Requests for another person's personal data.
- Questions requiring unavailable system lookups.
- Questions about personal leave balances.

NEVER:
- Invent company policies.
- Guess numbers, dates or rules.
- Reveal another employee's private information.
- Repeat personal identifiers unnecessarily.

OUTPUT REQUIREMENTS:

Return ONLY valid JSON containing these five fields:

{
  "answer": "string",
  "policy_section": "string",
  "answer_found": true,
  "needs_human": false,
  "escalation_reason": "string"
}

Use true or false for Boolean fields.

If answer_found is true, policy_section must contain
the supporting policy section.

If needs_human is true, escalation_reason must explain why.

If no policy section supports the answer, use an empty
string for policy_section.

Do not include Markdown formatting or code fences.
"""


def build_prompt(question):
    ids = pick_sections(question)

    policy_text = "\n".join(
        f"{sid} {POLICY[sid]}"
        for sid in ids
    )

    if not policy_text:
        policy_text = "(No matching policy section found.)"

    return (
        PROMPT_TEMPLATE
        .replace("{{policy_version}}", POLICY_VERSION)
        .replace("{{policy_text}}", policy_text)
        .replace("{{question}}", question)
    )


# ------------------------------------------------------------
# TODO 2: VALIDATION RULES
# ------------------------------------------------------------

FIELDS = [
    "answer",
    "policy_section",
    "answer_found",
    "needs_human",
    "escalation_reason",
]

SENSITIVE = [
    "unfair",
    "harass",
    "complain",
    "grievance",
    "fired",
    "terminat",
    "salary",
    "pay cut",
    "colleague",
    "my manager",
    "leave balance",
    "remaining leave",
]


def clean(raw):
    """Remove Markdown code fences from JSON responses."""

    text = (raw or "").strip()

    text = re.sub(
        r"^```(?:json)?",
        "",
        text
    ).strip()

    return re.sub(
        r"```$",
        "",
        text
    ).strip()


def validate(question, raw):
    """Validate the model response.

    Returns:
        (data, None) when validation succeeds.
        (None, reason) when validation fails.
    """

    # RULE 1: Check JSON structure.

    try:
        data = json.loads(clean(raw))

    except (json.JSONDecodeError, TypeError):
        return None, "not valid JSON"

    if not isinstance(data, dict):
        return None, "not valid JSON"

    if any(field not in data for field in FIELDS):
        return None, "a required field is missing"

    if (
        not isinstance(data["answer"], str)
        or not isinstance(data["policy_section"], str)
        or type(data["answer_found"]) is not bool
        or type(data["needs_human"]) is not bool
        or not isinstance(data["escalation_reason"], str)
    ):
        return None, "a field has an invalid type"

    # RULE 2: A found answer requires a policy section.

    if (
        data["answer_found"]
        and not data["policy_section"].strip()
    ):
        return None, "policy section is missing"

    # Check that cited sections exist and were retrieved.

    cited_sections = re.findall(
        r"\d+\.\d+",
        data["policy_section"]
    )

    if data["answer_found"]:
        allowed_sections = set(pick_sections(question))

        if (
            not cited_sections
            or any(
                section not in allowed_sections
                for section in cited_sections
            )
        ):
            return None, "unsupported policy section"

    # RULE 3: Sensitive questions require escalation.

    lower_question = question.lower()

    if any(
        word in lower_question
        for word in SENSITIVE
    ):
        data["needs_human"] = True

        if not data["escalation_reason"]:
            data["escalation_reason"] = (
                "This question requires human HR review."
            )

    if not data["answer_found"]:
        data["needs_human"] = True

        if not data["escalation_reason"]:
            data["escalation_reason"] = (
                "The approved policy does not clearly "
                "answer this question."
            )

    # RULE 4: Check numbers against the policy or question.

    if data["answer_found"]:
        supported_text = question + " "

        for section in cited_sections:
            supported_text += POLICY[section] + " "

        answer_numbers = re.findall(
            r"\d+(?:\.\d+)?",
            data["answer"]
        )

        supported_numbers = re.findall(
            r"\d+(?:\.\d+)?",
            supported_text
        )

        for number in answer_numbers:
            if number not in supported_numbers:
                return None, (
                    "answer contains an unsupported number"
                )

    return data, None


# ------------------------------------------------------------
# TODO 3: HR ESCALATION MESSAGE
# ------------------------------------------------------------

def hr_message(question, data, problem=None):
    """Prepare a message for the demonstration HR queue."""

    section = "None"
    reason = problem or "Human HR review required."

    if data is not None:
        section = data.get("policy_section") or "None"

        reason = (
            data.get("escalation_reason")
            or problem
            or "Human HR review required."
        )

    return (
        f"Employee question: {question}\n"
        f"Escalation reason: {reason}\n"
        f"Policy section: {section}"
    )


# ------------------------------------------------------------
# GOOGLE GEMINI API CONNECTION
# ------------------------------------------------------------

def get_key():
    """Read the Gemini API key securely."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key and str(key).strip():
            return str(key).strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip() or None    

def call_model(prompt):
    """Send the prompt to Google Gemini."""

    client = genai.Client(
        api_key=get_key()
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
        raise ValueError("Gemini returned an empty response")

    return response.text


RETRY_NOTE = """
Return only valid JSON containing all five required fields.
"""


# ------------------------------------------------------------
# RUN THE COMPLETE WORKFLOW
# ------------------------------------------------------------

def answer_question(question):
    """Build prompt, call Gemini, and validate its response."""

    prompt = build_prompt(question)

    data = None
    problem = "no reply"

    for attempt in range(2):

        try:
            if attempt == 0:
                raw = call_model(prompt)

            else:
                raw = call_model(
                    prompt + RETRY_NOTE
                )

        except Exception as error:
            return None, (
                "the model call failed "
                f"({type(error).__name__})"
            )

        data, problem = validate(
            question,
            raw
        )

        # Retry once if JSON is invalid or fields are missing.

        if problem is None:
            break

        if problem not in [
            "not valid JSON",
            "a required field is missing",
            "a field has an invalid type",
        ]:
            break

    return data, problem


# ------------------------------------------------------------
# STREAMLIT APPLICATION
# ------------------------------------------------------------

def main():

    st.set_page_config(
        page_title="Meridian HR assistant",
        page_icon="💬"
    )

    st.title("Meridian HR assistant")

    st.caption(
        "Fictional company. Answers come only from "
        f"policy version {POLICY_VERSION}."
    )

    # Check Gemini API key.

    if not get_key():

        st.error(
            "No Gemini API key found. "
            "Add GEMINI_API_KEY to Streamlit Secrets, "
            "then reboot the app."
        )

        st.stop()

    # Initialize chat and HR queue.

    if "chat" not in st.session_state:
        st.session_state.chat = []

    if "queue" not in st.session_state:
        st.session_state.queue = []

    if "last" not in st.session_state:
        st.session_state.last = None

    # Display previous chat messages.

    for role, message in st.session_state.chat:

        with st.chat_message(role):
            st.write(message)

    # Receive employee question.

    question = st.chat_input(
        "Ask an HR question"
    )

    if question:

        st.session_state.chat.append(
            ("user", question)
        )

        with st.chat_message("user"):
            st.write(question)

        # Run Gemini and validate the answer.

        data, problem = answer_question(question)

        st.session_state.last = data

        # Only show policy answers when validation succeeds.

        if (
            problem is None
            and data is not None
            and data["answer_found"]
            and data["answer"]
        ):

            reply = str(data["answer"])

            if data["needs_human"]:

                st.session_state.queue.append(
                    hr_message(question, data)
                )

                reply += (
                    "\n\nThis question has also been "
                    "added to the demonstration HR queue."
                )

        else:

            st.session_state.queue.append(
                hr_message(question, data, problem)
            )

            reply = (
                "I cannot confirm an answer from the "
                "approved policy. Your question has been "
                "added to the demonstration HR queue."
            )

        # Display assistant reply.

        st.session_state.chat.append(
            ("assistant", reply)
        )

        with st.chat_message("assistant"):
            st.write(reply)

    # Sidebar: demonstration HR queue.

    with st.sidebar:

        st.header("HR queue")

        if not st.session_state.queue:
            st.write("Nothing escalated yet.")

        for message in st.session_state.queue:
            st.code(message, language=None)

        with st.expander("Last structured answer"):
            st.json(st.session_state.last or {})


if __name__ == "__main__":
    main()
