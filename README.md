# NEXUS AI Automation Hub

Cloud-first learning project: Streamlit Community Cloud UI, Grok via xAI API, local RAG, MCP tools, and optional n8n webhook integration.

## Important deployment boundary

- You do not need to run the project on your personal computer.
- Streamlit Community Cloud hosts the Streamlit UI.
- Grok is called through the xAI API.
- The RAG knowledge documents and synthetic CSV data are included in this repository.
- `mcp_server.py` is a separate MCP service and must be deployed on a separate reachable host to be used remotely.
- n8n also needs its own hosted instance. Streamlit Community Cloud does not host n8n or a standalone MCP server.
- Free hosting for persistent n8n/MCP services is constrained; free tiers may sleep, have ephemeral storage, or change terms. We will validate a hosting choice before depending on it.
- All sample data is synthetic. No live routers, user accounts, security controls, or production systems are accessed or changed.

## GitHub-first deployment

You can upload the extracted project files to GitHub using the browser; local Python/CMD is not required for deployment.

1. Create a GitHub repository named `nexus-ai-automation-hub`.
2. Upload the files and folders from this project to the repository root.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Choose Create app, select your repository, branch `main`, and entrypoint `app.py`.
5. In Streamlit Community Cloud app settings, add secrets:
   ```toml
   GROK_API_KEY = "your-xai-api-key"
   GROK_MODEL = "grok-4.7"
   ```
6. Save and reboot/redeploy the app. Never place the API key in a source file or commit it to GitHub.

Get an xAI API key from https://console.x.ai/. API access and usage may incur charges; hosting may be free while model inference is not necessarily free.

## App features

- Streamlit dashboard
- Synthetic incident register
- Local TF-IDF retrieval over Markdown runbooks (a simple RAG baseline)
- Grok-powered analysis using retrieved context
- Reusable deterministic tools shared with MCP server
- Optional n8n webhook caller
- Simulation-only safety boundary

## MCP server

`mcp_server.py` exposes tools:
- `search_knowledge_base`
- `list_synthetic_incidents`
- `analyze_synthetic_incident`
- `create_simulated_incident_report`

It uses Streamable HTTP transport when run as a standalone service. Do not assume it is publicly reachable just because the Streamlit app is deployed.

## Secrets

- `GROK_API_KEY`: required for Grok analysis.
- `GROK_MODEL`: optional; defaults to `grok-4.7`.
- `N8N_WEBHOOK_URL`: optional; enables the n8n webhook tab.

Use Streamlit's Secrets settings, not GitHub files, for these values.

## Dependencies

`requirements.txt` defines the Python packages installed by Streamlit Community Cloud. This project targets Python 3.12 where available. If a package major version introduces a breaking API, update and test the code before upgrading.

## Local tests (optional, not required for cloud deployment)

```bash
python -m unittest discover -s tests -v
```

## Next milestones

1. Deploy and verify Streamlit + Grok + RAG.
2. Host and test the MCP server on a separate service.
3. Host n8n and import a simulation-only workflow.
4. Connect n8n to MCP and display workflow progress/audit output in Streamlit.
