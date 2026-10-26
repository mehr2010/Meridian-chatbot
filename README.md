# Meridian HR chatbot (training project)

A small HR chatbot built in the AI Datayard, AI Automation Bootcamp, Module 2.
It answers employee questions from a fictional company policy using GEMINI , checks each answer
with validation rules, and sends anything sensitive or unclear to an HR queue.

All names, policies and data are fictional.

## Files

- `hr_chatbot.py` - the app
- `requirements.txt` - the packages Streamlit Community Cloud installs (`streamlit`, `google-genai`)

## How it runs

The app is deployed with Streamlit Community Cloud, which launches it directly from this repo.
Follow the Module 2 Build Guide for the full steps.

## Keep your key safe

Never put your GEMINI API key in this repo, in the code or in this README. Add it only in the app's
Secrets settings, as one line:

    GEMINI_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"

Keep this repo private, and delete the app and the key when you no longer need them.
