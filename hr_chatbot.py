"""
Meridian Logistics HR Assistant
AI DataYard - Module 2, Lab 4

Google Gemini + Streamlit
Fictional HR policies for demonstration purposes.
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
# 3. POLICY SECTION SELECTION
# ============================================================

KEYWORDS = {
    "1.1": ["annual leave", "leave days", "vacation"],
    "1.2": ["carry", "lapse", "unused leave"],
    "1.3": ["notice", "days off", "take leave", "time off"],
    "2.1": ["sick", "doctor", "medical certificate"],
    "3.1": ["working hours", "start time", "grace"],
    "3.2": ["work from home", "remote", "wfh"],
    "4.1": ["insurance", "parents", "spouse", "children"],
    "5.1": ["salary", "pay", "personal data", "colleague"],
}


def pick_sections(question):
    q = question.lower()

    return [
        sid
        for sid, words in KEYWORDS.items()
        if any(word in q for word in words)
    ]


# ============================================================
# 4. GROUNDED HR PROMPT
# ============================================================

PROMPT_TEMPLATE = """
You are an HR assistant at Meridian Logistics.

POLICY VERSION:
{{policy_version}}

APPROVED HR POLICY:
{{policy_text}}

EMPLOYEE QUESTION:
{{question}}

INSTRUCTIONS:

1. Answer ONLY using the approved HR policy.
2. Do not invent policies, dates, numbers or rules.
3. Answer in plain language using no more than 3 sentences.
4. Include the supporting policy section.
5. If the policy does not answer the question:
   - Set answer_found to false.
   - Set needs_human to true.
   - Explain the reason.

ALWAYS ESCALATE:
- Complaints about managers or colleagues.
- Harassment, grievances or pay disputes.
- Termination and sensitive medical details.
- Requests for another person's personal information.
- Questions requiring unavailable system lookups.
- Personal leave balance questions.

NEVER:
- Guess missing policy information.
- Reveal another employee's personal data.
- Repeat unnecessary personal identifiers.

RETURN ONLY VALID JSON WITH THESE FIVE FIELDS:

{
    "answer": "string",
    "policy_section": "string",
    "answer_found": true,
    "needs_human": false,
    "escalation_reason": "string"
}

Use true or false for Boolean values.

If answer_found is true, provide a supporting policy section.

If no section supports the answer, use an empty string
for policy_section.

If needs_human is true, explain why in escalation_reason.

Do not return Markdown or code fences.
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


# ============================================================
# 5. RESPONSE VALIDATION
# ============================================================

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
    "complaint",
    "grievance",
    "fired",
    "terminat",
    "salary",
    "pay cut",
    "pay dispute",
    "colleague",
    "my manager",
    "leave balance",
    "remaining leave",
]


def clean(raw):
    text = (raw or "").strip()

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

    return text


def validate(question, raw):
    """
    Validate JSON, policy sections, sensitive questions,
    and numeric claims.
    """

    # RULE 1: Valid JSON and required fields
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

    # RULE 2: Validate cited policy sections
    cited_sections = re.findall(
        r"\d+\.\d+",
        data["policy_section"]
    )

    allowed_sections = set(pick_sections(question))

    if data["answer_found"]:
        if not cited_sections:
            return None, "policy section is missing"

        if any(
            section not in allowed_sections
            for section in cited_sections
        ):
            return None, "unsupported policy section"

    # RULE 3: Escalate sensitive questions
    lower_question = question.lower()

    if any(word in lower_question for word in SENSITIVE):
        data["needs_human"] = True

        if not data["escalation_reason"].strip():
            data["escalation_reason"] = (
                "This question requires human HR review."
            )

    if not data["answer_found"]:
        data["needs_human"] = True

        if not data["escalation_reason"].strip():
            data["escalation_reason"] = (
                "The approved policy does not clearly "
                "answer this question."
            )

    # RULE 4: Validate numbers
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
                return None, "answer contains an unsupported number"

    return data, None


# ============================================================
# 6. HR ESCALATION MESSAGE
# ============================================================

def hr_message(question, data, problem=None):
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


# ============================================================
# 7. GEMINI API KEY CONFIGURATION
# ============================================================

def get_key():
    """
    Read the API key from Streamlit Secrets first,
    then from environment variables.
    """

    try:
        key = st.secrets.get("GEMINI_API_KEY", "")

        if key and str(key).strip():
            return str(key).strip()

    except Exception:
        pass

    key = os.environ.get("GEMINI_API_KEY", "")

    return key.strip() or None


def check_secret_status():
    """
    Safe diagnostic. Never displays the actual API key.
    """

    try:
        found = "GEMINI_API_KEY" in st.secrets

        if not found:
            return "Secret name not found in Streamlit Secrets"

        value = st.secrets.get("GEMINI_API_KEY", "")

        if not str(value).strip():
            return "Secret exists but its value is empty"

        return "Secret found with a nonempty value"

    except Exception as error:
        return (
            "Secrets could not be read: "
            + type(error).__name__
        )


# ============================================================
# 8. GOOGLE GEMINI API CONNECTION
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
        raise ValueError("Gemini returned an empty response")

    return response.text


RETRY_NOTE = """
Return only valid JSON containing all five required fields.
Do not include Markdown or code fences.
"""


# ============================================================
# 9. COMPLETE QUESTION WORKFLOW
# ============================================================

def answer_question(question):
    prompt = build_prompt(question)

    data = None
    problem = "no reply"

    for attempt in range(2):
        try:
            if attempt == 0:
                raw = call_model(prompt)
            else:
                raw = call_model(prompt + RETRY_NOTE)

        except Exception as error:
            return None, (
                "Gemini request failed: "
                f"{type(error).__name__}"
            )

        data, problem = validate(question, raw)

        if problem is None:
            break

        retry_problems = [
            "not valid JSON",
            "a required field is missing",
            "a field has an invalid type",
        ]

        if problem not in retry_problems:
            break

    return data, problem


# ============================================================
# 10. STREAMLIT APPLICATION
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
    # API KEY CHECK AND SAFE DIAGNOSTIC
    # --------------------------------------------------------

    api_key = get_key()

    if not api_key:
        st.error("Gemini API key not detected.")

        st.write(
            "Secrets diagnostic:",
            check_secret_status()
        )

        st.info(
            "The application is running, but Gemini "
            "cannot be used until the API key is available."
        )

        st.markdown(
            """
### Check your Streamlit Secrets

Open the deployed app's Settings, then Secrets.

The entry should be:

```toml
GEMINI_API_KEY = "YOUR_REAL_GEMINI_API_KEY"
```

Replace the placeholder with your actual key.

Save the changes and reboot the app.

Do not share your API key or upload it to GitHub.
            """
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
    # DISPLAY CHAT HISTORY
    # --------------------------------------------------------

    for role, message in st.session_state.chat:
        with st.chat_message(role):
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

        # Call Gemini
        with st.spinner("Checking HR policy..."):
            data, problem = answer_question(question)

        st.session_state.last = data

        # ----------------------------------------------------
        # DISPLAY VALIDATED ANSWER
        # ----------------------------------------------------

        if (
            problem is None
            and data is not None
            and data["answer_found"]
            and data["answer"]
        ):
            reply = data["answer"]

            if data["policy_section"]:
                reply += (
                    "\n\nPolicy section: "
                    + data["policy_section"]
                )

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
                "approved HR policy. Your question has "
                "been added to the demonstration HR queue."
            )

        # Save and display reply
        st.session_state.chat.append(
            ("assistant", reply)
        )

        with st.chat_message("assistant"):
            st.write(reply)

    # --------------------------------------------------------
    # HR ESCALATION SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:
        st.header("HR Queue")

        st.caption(
            "Demonstration only. Entries are not "
            "sent to a real HR department."
        )

        if not st.session_state.queue:
            st.write("Nothing escalated yet.")

        for message in st.session_state.queue:
            st.code(message, language=None)

        with st.expander("Last structured answer"):
            st.json(st.session_state.last or {})


# ============================================================
# 11. START APPLICATION
# ============================================================

if __name__ == "__main__":
    main()
