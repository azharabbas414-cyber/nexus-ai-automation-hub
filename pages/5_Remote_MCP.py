"""Remote MCP tools page for NEXUS AI Automation Hub.

The MCP bearer token is read only from Streamlit secrets and is never displayed.
This page connects to the separately hosted Cloudflare Worker using Streamable HTTP.
"""
import asyncio
import json
import streamlit as st
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "https://nexus-ai-mcp.azhar-abbas414.workers.dev/mcp"


def get_mcp_token() -> str:
    try:
        return str(st.secrets.get("MCP_API_TOKEN", "")).strip()
    except Exception:
        return ""


async def _list_remote_tools(token: str) -> list[dict]:
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


async def _call_remote_tool(token: str, tool_name: str, arguments: dict) -> dict:
    async with streamablehttp_client(
        MCP_URL,
        headers={"Authorization": f"Bearer {token}"},
    ) as (read_stream, write_stream, _session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            content = []
            for item in result.content:
                if getattr(item, "type", "") == "text":
                    text = item.text
                    try:
                        content.append(json.loads(text))
                    except (json.JSONDecodeError, TypeError):
                        content.append(text)
                else:
                    content.append({"type": getattr(item, "type", "unknown")})
            return {
                "tool": tool_name,
                "is_error": bool(getattr(result, "isError", False)),
                "content": content,
                "structured_content": getattr(result, "structuredContent", None),
            }


def run_async(coro):
    """Run one short MCP operation from Streamlit's synchronous script."""
    return asyncio.run(coro)


st.set_page_config(page_title="NEXUS AI · Remote MCP", page_icon="🔌", layout="wide")
st.title("🔌 Remote MCP Connection")
st.caption("Connects NEXUS AI to the Cloudflare-hosted MCP Worker. Demo data only; no live systems are contacted.")
st.info("The MCP token is read from Streamlit Secrets. This page never prints or returns the token.")

token = get_mcp_token()
if not token:
    st.error("MCP_API_TOKEN is not configured in Streamlit Community Cloud → app Settings → Secrets.")
    st.markdown("Add `MCP_API_TOKEN` there using the same secret value configured in Cloudflare. Do not add it to GitHub or paste it into this page.")
    st.stop()

left, right = st.columns([1, 2])
with left:
    st.write("**Worker endpoint**")
    st.code(MCP_URL, language="text")
    if st.button("Connect and list tools", type="primary", use_container_width=True):
        try:
            with st.spinner("Connecting to the remote MCP Worker..."):
                tools = run_async(_list_remote_tools(token))
            st.session_state["remote_mcp_tools"] = tools
            st.session_state["remote_mcp_connection_ok"] = True
            st.success(f"Connected. Found {len(tools)} tools.")
        except Exception as exc:
            st.session_state["remote_mcp_connection_ok"] = False
            # Show the exception text, but never show request headers or the token.
            st.error("Connection failed. Check that the Cloudflare secret and Streamlit secret match, and that the Worker is deployed.")
            st.caption(f"Technical detail: {type(exc).__name__}: {str(exc)[:500]}")

with right:
    if st.session_state.get("remote_mcp_connection_ok"):
        st.success("MCP connection initialized.")
    else:
        st.caption("Click **Connect and list tools** to check the connection.")

tools = st.session_state.get("remote_mcp_tools", [])
if tools:
    st.subheader("Available remote tools")
    st.dataframe(
        [{"Tool": item["name"], "Description": item["description"]} for item in tools],
        use_container_width=True,
        hide_index=True,
    )

    tool_names = [item["name"] for item in tools]
    selected_tool = st.selectbox("Choose an MCP tool to run", tool_names)
    arguments = {}

    if selected_tool == "list_incidents":
        st.write("Optional filters — leave a field blank to include all values.")
        c1, c2 = st.columns(2)
        with c1:
            category = st.text_input("Category", placeholder="e.g. Telecom")
            priority = st.selectbox("Priority", ["Any", "Critical", "High", "Medium", "Low"])
        with c2:
            status = st.selectbox("Status", ["Any", "Open", "Investigating", "Closed"])
            region = st.text_input("Region", placeholder="e.g. North")
        if category.strip():
            arguments["category"] = category.strip()
        if priority != "Any":
            arguments["priority"] = priority
        if status != "Any":
            arguments["status"] = status
        if region.strip():
            arguments["region"] = region.strip()

    elif selected_tool in ("analyze_incident", "generate_incident_report"):
        arguments["incident_id"] = st.text_input("Incident ID", value="NX-1002").strip()

    elif selected_tool == "search_knowledge":
        arguments["query"] = st.text_input("Knowledge search query", value="BGP")
        arguments["top_k"] = st.selectbox("Maximum documents", [1, 2, 3], index=2)

    else:
        st.warning("This page has no input form for this tool yet. Review the tool schema above before calling it.")
        selected_schema = next((item["input_schema"] for item in tools if item["name"] == selected_tool), {})
        st.json(selected_schema)
        st.stop()

    if st.button("Run selected MCP tool", type="primary"):
        try:
            with st.spinner(f"Running {selected_tool}..."):
                output = run_async(_call_remote_tool(token, selected_tool, arguments))
            if output["is_error"]:
                st.warning("The MCP tool returned an error.")
            st.subheader("Tool result")
            st.json(output)
        except Exception as exc:
            st.error("The MCP tool call failed. Check the Cloudflare deployment and authentication secret.")
            st.caption(f"Technical detail: {type(exc).__name__}: {str(exc)[:500]}")

st.divider()
st.caption("Security: MCP_API_TOKEN is held in Streamlit Secrets and sent server-to-server. Never put the token in client-side code, screenshots, or GitHub.")
