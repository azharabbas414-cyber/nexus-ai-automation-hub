import os
import json
import asyncio
import requests
import pandas as pd
import streamlit as st

from core_tools import load_incidents, retrieve_knowledge, analyze_incident, generate_incident_report
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

APP_TITLE = "NEXUS AI Automation Hub"
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MCP_URL = "https://nexus-ai-mcp.azhar-abbas414.workers.dev/mcp"

st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: 12px; border-radius: 12px;}
.nexus-subtitle {color: #9ca3af; font-size: .92rem;}
</style>
""", unsafe_allow_html=True)


def get_secret(name: str, default: str = "") -> str:
    """Read a Streamlit secret first, then an environment variable."""
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def ask_grok(question: str, context: str, model: str) -> str:
    """Call Groq through its OpenAI-compatible Chat Completions endpoint."""
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        return (
            "Groq is not configured yet. Add GROQ_API_KEY in Streamlit Community Cloud → "
            "your app → Settings → Secrets, then retry. Your question and retrieved context "
            "are ready; no key is stored in GitHub."
        )
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=45.0)
    system_prompt = (
        "You are NEXUS AI, a careful enterprise analysis assistant. "
        "Use the provided local knowledge and synthetic incident context. "
        "Separate facts from hypotheses. Never claim you executed a real-world action. "
        "All data in this project is synthetic and all actions are simulations. "
        "If context is insufficient, say what is missing. Provide a concise summary, "
        "likely causes, recommended checks, and safe next steps."
    )
    user_prompt = f"""Question:
{question}
Retrieved local knowledge and synthetic incident context:
{context}
Respond with:
1. Summary
2. Evidence from the supplied context
3. Possible explanations (label hypotheses)
4. Safe next steps
5. What to verify next
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or "The model returned an empty response."


def call_n8n_webhook(payload: dict) -> dict:
    """Optional outbound call to a user-configured n8n webhook."""
    url = get_secret("N8N_WEBHOOK_URL")
    if not url:
        return {
            "ok": False,
            "message": "N8N_WEBHOOK_URL is not configured. You can use the local demo without n8n."
        }
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = {"response_text": response.text[:3000]}
        return {"ok": True, "status_code": response.status_code, "data": data}
    except requests.RequestException as exc:
        return {"ok": False, "message": f"n8n request failed: {exc}"}
