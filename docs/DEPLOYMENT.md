# Browser-only deployment guide

## Part A — GitHub

1. Sign in at https://github.com/.
2. Create a new repository called `nexus-ai-automation-hub`.
3. For this starter, upload the extracted project contents to the repository root (not the containing parent folder).
4. Confirm `app.py`, `requirements.txt`, `core_tools.py`, `mcp_server.py`, `knowledge/`, and `data/` are visible at the root.

## Part B — xAI / Grok key

1. Sign in at https://console.x.ai/.
2. Create an API key using the account's current API console instructions.
3. Do not share the key in chat or put it into a GitHub file.
4. Note that API access can require billing/credits; Streamlit hosting being free does not make Grok API calls free.

## Part C — Streamlit Community Cloud

1. Sign in at https://share.streamlit.io/ using the same GitHub account.
2. Click Create app.
3. Select `nexus-ai-automation-hub`, branch `main`, and `app.py`.
4. Open advanced settings / secrets and paste:
   ```toml
   GROK_API_KEY = "paste-your-private-key-here"
   GROK_MODEL = "grok-4.7"
   ```
5. Deploy and wait for the build.
6. Check the app opens. The dashboard works without a Grok key, but AI analysis needs a valid key.
7. Test the incident register and Tool Playground first, then test Grok.

## Part D — Optional integrations

Do not set `N8N_WEBHOOK_URL` until a separately hosted n8n webhook exists. Do not assume Streamlit Cloud can host an always-on n8n service or the standalone MCP server.

MCP and n8n hosting will be a separate milestone. We'll select a currently available free-tier option and verify persistence, sleeping, networking, and public endpoint support before wiring it into this app.
