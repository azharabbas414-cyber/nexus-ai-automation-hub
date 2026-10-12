import os
import json
import requests
import pandas as pd
import streamlit as st

from core_tools import load_incidents, retrieve_knowledge, analyze_incident, generate_incident_report

APP_TITLE = "NEXUS AI Automation Hub"
DEFAULT_MODEL = os.getenv("GROK_MODEL", "grok-4.7")

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
    """Call the xAI API through its OpenAI-compatible Chat Completions endpoint."""
    api_key = get_secret("GROK_API_KEY")
    if not api_key:
        return (
            "Grok is not configured yet. Add GROK_API_KEY in Streamlit Community Cloud → "
            "your app → Settings → Secrets, then retry. Your question and retrieved context "
            "are ready; no key is stored in GitHub."
        )

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=45.0)
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

st.title("🧭 NEXUS AI Automation Hub")
st.markdown('<p class="nexus-subtitle">Grok + local RAG + MCP-ready tools + n8n workflow integration</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Configuration")
    model = st.text_input("Grok model", value=get_secret("GROK_MODEL", DEFAULT_MODEL))
    api_configured = bool(get_secret("GROK_API_KEY"))
    n8n_configured = bool(get_secret("N8N_WEBHOOK_URL"))
    st.write("Grok API:", "🟢 Configured" if api_configured else "🟡 Not configured")
    st.write("n8n webhook:", "🟢 Configured" if n8n_configured else "⚪ Optional")
    st.caption("API credentials must be added to Streamlit Secrets, never to GitHub.")
    st.caption("This app uses synthetic data and simulated actions only.")

incidents = load_incidents()
documents = retrieve_knowledge("network cybersecurity business data incident", top_k=3)

open_count = int((incidents["status"].str.lower() != "closed").sum()) if not incidents.empty else 0
high_count = int(incidents["priority"].str.lower().isin(["high", "critical"]).sum()) if not incidents.empty else 0
c1, c2, c3, c4 = st.columns(4)
c1.metric("Synthetic incidents", len(incidents))
c2.metric("Open incidents", open_count)
c3.metric("High / critical", high_count)
c4.metric("Knowledge documents", len(documents))

tab_chat, tab_incidents, tab_tools, tab_workflow = st.tabs(
    ["💬 AI Analyst", "📋 Incident Register", "🧰 Tool Playground", "🔄 n8n Workflow"]
)

with tab_chat:
    st.subheader("Ask NEXUS AI")
    st.write("Ask a question about the sample incidents or the local runbooks. The app retrieves relevant text and passes it to Grok.")
    question = st.text_area(
        "Your question",
        placeholder="Example: Investigate the simulated BGP peer flapping incident. What should we check first?",
        height=100,
        key="analyst_question",
    )
    if st.button("Analyze with Grok", type="primary", key="analyze_grok"):
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            retrieved = retrieve_knowledge(question, top_k=3)
            incident_context = incidents.to_csv(index=False) if not incidents.empty else "No incident records."
            knowledge_context = "\n\n".join(
                f"Document: {d['title']}\n{d['content']}" for d in retrieved
            ) or "No matching local knowledge documents."
            context = f"INCIDENT DATA:\n{incident_context}\n\nKNOWLEDGE:\n{knowledge_context}"
            with st.spinner("Retrieving context and asking Grok..."):
                try:
                    answer = ask_grok(question, context, model.strip() or DEFAULT_MODEL)
                    st.markdown(answer)
                    st.session_state["last_analysis"] = {
                        "question": question,
                        "answer": answer,
                        "retrieved_documents": [d["title"] for d in retrieved],
                    }
                except Exception as exc:
                    st.error(f"Grok request failed: {exc}")
                    st.info("Check that GROK_API_KEY is valid, your model is available to your account, and the key has API credits/permissions.")

    if st.session_state.get("last_analysis"):
        with st.expander("Show RAG retrieval trace"):
            st.json(st.session_state["last_analysis"]["retrieved_documents"])
            st.caption("The retrieved document names help you inspect which local knowledge was passed to the model.")

with tab_incidents:
    st.subheader("Synthetic incident register")
    if not incidents.empty:
        priorities = st.multiselect(
            "Filter by priority",
            sorted(incidents["priority"].dropna().unique().tolist()),
            default=sorted(incidents["priority"].dropna().unique().tolist()),
        )
        view = incidents[incidents["priority"].isin(priorities)]
        st.dataframe(view, use_container_width=True, hide_index=True)
        selected_id = st.selectbox("Select an incident for a deterministic analysis", incidents["incident_id"].tolist())
        selected = incidents[incidents["incident_id"] == selected_id].iloc[0].to_dict()
        if st.button("Analyze selected incident"):
            st.json(analyze_incident(selected))
    else:
        st.warning("No sample incidents found.")

with tab_tools:
    st.subheader("MCP-ready tools")
    st.write("These safe functions are implemented in `core_tools.py` and are also exposed by the standalone MCP server in `mcp_server.py`.")
    tool_choice = st.selectbox("Choose a tool", ["search_knowledge_base", "analyze_incident", "generate_incident_report"])
    if tool_choice == "search_knowledge_base":
        tool_query = st.text_input("Search query", "BGP peer flapping")
        if st.button("Run knowledge search"):
            st.json(retrieve_knowledge(tool_query, top_k=3))
    elif tool_choice == "analyze_incident":
        tool_id = st.selectbox("Incident ID", incidents["incident_id"].tolist())
        if st.button("Run incident analysis"):
            row = incidents[incidents["incident_id"] == tool_id].iloc[0].to_dict()
            st.json(analyze_incident(row))
    else:
        report_id = st.selectbox("Incident ID for report", incidents["incident_id"].tolist(), key="report_id")
        if st.button("Generate simulated report"):
            row = incidents[incidents["incident_id"] == report_id].iloc[0].to_dict()
            st.text(generate_incident_report(row))

with tab_workflow:
    st.subheader("Optional n8n workflow call")
    st.write("Once a hosted n8n webhook is configured in Streamlit Secrets, this button sends a synthetic incident payload to it.")
    selected_workflow_id = st.selectbox("Incident to send", incidents["incident_id"].tolist(), key="workflow_id")
    if st.button("Send synthetic event to n8n"):
        row = incidents[incidents["incident_id"] == selected_workflow_id].iloc[0].to_dict()
        payload = {
            "source": "nexus-ai-streamlit",
            "mode": "simulation_only",
            "incident": row,
            "requested_action": "prepare_report",
        }
        with st.spinner("Calling configured n8n webhook..."):
            result = call_n8n_webhook(payload)
        if result.get("ok"):
            st.success("n8n webhook responded.")
        else:
            st.warning(result.get("message", "Webhook not configured or request failed."))
        st.json(result)

st.divider()
st.caption("NEXUS AI Automation Hub · Synthetic training data only · No production systems or live network devices are contacted.")
