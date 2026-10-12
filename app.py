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


async def list_remote_mcp_tools(token: str) -> list[dict]:
    """List tools exposed by the Cloudflare MCP Worker."""
    async with streamablehttp_client(
        MCP_URL,
        headers={"Authorization": f"Bearer {token}"},
    ) as (read_stream, write_stream, _session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": getattr(tool, "inputSchema", {}),
                }
                for tool in result.tools
            ]


async def call_remote_mcp_tool(token: str, tool_name: str, arguments: dict) -> dict:
    """Call a remote MCP tool without exposing the token in the UI."""
    async with streamablehttp_client(
        MCP_URL,
        headers={"Authorization": f"Bearer {token}"},
    ) as (read_stream, write_stream, _session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            output = []
            for item in result.content:
                if getattr(item, "type", "") == "text":
                    try:
                        output.append(json.loads(item.text))
                    except (json.JSONDecodeError, TypeError):
                        output.append(item.text)
                else:
                    output.append({"type": getattr(item, "type", "unknown")})
            return {
                "tool": tool_name,
                "is_error": bool(getattr(result, "isError", False)),
                "content": output,
            }


def run_async(coro):
    """Run a short MCP operation from Streamlit's synchronous script."""
    return asyncio.run(coro)



def build_remote_mcp_context(question: str, token: str) -> tuple[str, list[str]]:
    """Select one synthetic-data MCP tool from a natural-language question."""
    import re
    q = question.lower()
    match = re.search(r"\bNX-\d{4}\b", question, re.IGNORECASE)
    incident_id = match.group(0).upper() if match else ""

    if any(term in q for term in ("generate report", "write a report", "incident report")):
        tool_name, args = "generate_incident_report", {"incident_id": incident_id or "NX-1002"}
    elif incident_id and any(term in q for term in ("analy", "investigat", "triage", "explain", "recommend", "why")):
        tool_name, args = "analyze_incident", {"incident_id": incident_id}
    elif any(term in q for term in ("list incidents", "show incidents", "open incidents", "all incidents", "incident register")):
        tool_name, args = "list_incidents", {}
        if "critical" in q:
            args["priority"] = "Critical"
        elif "high" in q:
            args["priority"] = "High"
        if any(term in q for term in ("telecom", "bgp", "network")):
            args["category"] = "Telecom"
        if "open" in q:
            args["status"] = "Open"
    elif any(term in q for term in ("analy", "investigat", "triage", "bgp", "flapping", "packet loss", "incident", "router", "network")):
        tool_name, args = "analyze_incident", {"incident_id": incident_id or "NX-1002"}
    else:
        tool_name, args = "search_knowledge", {"query": question, "top_k": 3}

    result = run_async(call_remote_mcp_tool(token, tool_name, args))
    return json.dumps(result, indent=2, ensure_ascii=False), [tool_name]

st.title("🧭 NEXUS AI Automation Hub")
st.markdown('<p class="nexus-subtitle">Groq + local RAG + MCP-ready tools + n8n workflow integration</p>', unsafe_allow_html=True)
with st.sidebar:
    st.header("Configuration")
    model = st.text_input("Groq model", value=get_secret("GROQ_MODEL", DEFAULT_MODEL))
    api_configured = bool(get_secret("GROQ_API_KEY"))
    n8n_configured = bool(get_secret("N8N_WEBHOOK_URL"))
    st.write("Groq API:", "🟢 Configured" if api_configured else "🟡 Not configured")
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

tab_chat, tab_incidents, tab_tools, tab_workflow, tab_remote_mcp = st.tabs(
    ["💬 AI Analyst", "📋 Incident Register", "🧰 Tool Playground", "🔄 n8n Workflow", "🔌 Remote MCP"]
)

with tab_chat:
    st.subheader("Ask NEXUS AI")
    st.write("Ask a question about sample incidents or runbooks. Optionally let the analyst call Cloudflare Remote MCP tools and include their results in the Groq analysis.")
    mcp_for_analyst = st.checkbox(
        "Use Cloudflare Remote MCP tools for this analysis",
        value=False,
        help="Selects one remote tool against synthetic demo data only; no live network devices are contacted.",
        key="analyst_use_remote_mcp",
    )
    question = st.text_area(
        "Your question",
        placeholder="Example: Investigate the simulated BGP peer flapping incident. What should we check first?",
        height=100,
        key="analyst_question",
    )
    if st.button("Analyze with Groq", type="primary", key="analyze_grok"):
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            retrieved = retrieve_knowledge(question, top_k=3)
            incident_context = incidents.to_csv(index=False) if not incidents.empty else "No incident records."
            knowledge_context = "\n\n".join(
                f"Document: {d['title']}\n{d['content']}" for d in retrieved
            ) or "No matching local knowledge documents."
            context = f"INCIDENT DATA:\n{incident_context}\n\nLOCAL KNOWLEDGE:\n{knowledge_context}"
            remote_tool_names_used = []
            with st.spinner("Retrieving context and asking Groq..."):
                try:
                    if mcp_for_analyst:
                        mcp_token_for_analyst = get_secret("MCP_API_TOKEN")
                        if not mcp_token_for_analyst:
                            st.warning("MCP_API_TOKEN is missing from Streamlit Secrets.")
                        else:
                            remote_context, remote_tool_names_used = build_remote_mcp_context(
                                question, mcp_token_for_analyst
                            )
                            context += f"\n\nCLOUDFLARE REMOTE MCP RESULT (synthetic demo data):\n{remote_context}"
                            st.caption("Remote MCP tool selected: " + ", ".join(remote_tool_names_used))
                    answer = ask_grok(question, context, model.strip() or DEFAULT_MODEL)
                    st.markdown(answer)
                    st.session_state["last_analysis"] = {
                        "question": question,
                        "answer": answer,
                        "retrieved_documents": [d["title"] for d in retrieved],
                        "remote_mcp_tools": remote_tool_names_used,
                    }
                except Exception as exc:
                    st.error(f"Groq request failed: {exc}")
                    st.info("Check that GROQ_API_KEY is valid, the model ID is available to your Groq account, and your account has API access.")
    if st.session_state.get("last_analysis"):
        with st.expander("Show RAG retrieval trace"):
            st.json(st.session_state["last_analysis"]["retrieved_documents"])
            st.caption("The retrieved document names help you inspect which local knowledge was passed to the model.")
            if st.session_state["last_analysis"].get("remote_mcp_tools"):
                st.write("Remote MCP tools used:")
                st.json(st.session_state["last_analysis"]["remote_mcp_tools"])

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

with tab_remote_mcp:
    st.subheader("Cloudflare Remote MCP Connection")
    st.write("Connect to the separately deployed NEXUS AI MCP Worker. This uses synthetic demo data only; it does not contact live routers or production systems.")
    st.caption(f"Endpoint: {MCP_URL}")
    mcp_token = get_secret("MCP_API_TOKEN")
    if not mcp_token:
        st.warning("MCP_API_TOKEN is not configured in Streamlit Secrets yet.")
        st.write("Open Streamlit Community Cloud → your app → Settings → Secrets, and add the same token you configured in Cloudflare. Never put the token in GitHub.")
    else:
        if st.button("Connect and list remote tools", type="primary", key="connect_remote_mcp"):
            try:
                with st.spinner("Connecting to Cloudflare MCP..."):
                    remote_tools = run_async(list_remote_mcp_tools(mcp_token))
                st.session_state["remote_mcp_tools"] = remote_tools
                st.session_state["remote_mcp_connected"] = True
                st.success(f"Connected successfully. Found {len(remote_tools)} tools.")
            except Exception as exc:
                st.session_state["remote_mcp_connected"] = False
                st.error("Connection failed. Confirm the Cloudflare and Streamlit MCP_API_TOKEN values match and the latest Worker deployment is active.")
                st.caption(f"Technical detail: {type(exc).__name__}: {str(exc)[:400]}")

        remote_tools = st.session_state.get("remote_mcp_tools", [])
        if remote_tools:
            st.dataframe(
                [{"Tool": tool["name"], "Description": tool["description"]} for tool in remote_tools],
                use_container_width=True,
                hide_index=True,
            )
            remote_tool_names = [tool["name"] for tool in remote_tools]
            remote_tool = st.selectbox("Choose remote MCP tool", remote_tool_names, key="remote_mcp_tool")
            remote_args = {}

            if remote_tool == "list_incidents":
                st.write("Optional filters. Leave blank or choose Any to include all incidents.")
                a, b = st.columns(2)
                with a:
                    remote_category = st.text_input("Category filter", key="remote_category", placeholder="e.g. Telecom")
                    remote_priority = st.selectbox("Priority filter", ["Any", "Critical", "High", "Medium", "Low"], key="remote_priority")
                with b:
                    remote_status = st.selectbox("Status filter", ["Any", "Open", "Investigating", "Closed"], key="remote_status")
                    remote_region = st.text_input("Region filter", key="remote_region", placeholder="e.g. North")
                if remote_category.strip():
                    remote_args["category"] = remote_category.strip()
                if remote_priority != "Any":
                    remote_args["priority"] = remote_priority
                if remote_status != "Any":
                    remote_args["status"] = remote_status
                if remote_region.strip():
                    remote_args["region"] = remote_region.strip()
            elif remote_tool in ("analyze_incident", "generate_incident_report"):
                remote_args["incident_id"] = st.text_input("Incident ID", value="NX-1002", key="remote_incident_id").strip()
            elif remote_tool == "search_knowledge":
                remote_args["query"] = st.text_input("Knowledge query", value="BGP", key="remote_knowledge_query")
                remote_args["top_k"] = st.selectbox("Maximum documents", [1, 2, 3], index=2, key="remote_knowledge_top_k")
            else:
                st.warning("This tool is not yet wired to a dedicated input form.")
                st.json(next((tool["input_schema"] for tool in remote_tools if tool["name"] == remote_tool), {}))

            if st.button("Run remote MCP tool", type="primary", key="run_remote_mcp"):
                try:
                    with st.spinner(f"Running {remote_tool}..."):
                        remote_result = run_async(call_remote_mcp_tool(mcp_token, remote_tool, remote_args))
                    if remote_result["is_error"]:
                        st.warning("The remote MCP tool returned an error.")
                    st.subheader("Remote MCP result")
                    st.json(remote_result)
                except Exception as exc:
                    st.error("The remote MCP tool call failed. Check the Worker deployment and matching secrets.")
                    st.caption(f"Technical detail: {type(exc).__name__}: {str(exc)[:400]}")

st.divider()
st.caption("NEXUS AI Automation Hub · Synthetic training data only · No production systems or live network devices are contacted.")
