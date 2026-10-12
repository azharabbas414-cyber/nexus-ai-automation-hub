# NEXUS MCP server — cloud deployment

## What this service does

The standalone MCP service exposes four tools over Streamable HTTP:
- `search_knowledge_base`
- `list_synthetic_incidents`
- `analyze_synthetic_incident`
- `create_simulated_incident_report`

It reads only the synthetic CSV and Markdown runbooks in this repository.

## Important security note

The tools return synthetic training data only. The `MCP_API_TOKEN` environment variable and `/authorize` route provide a basic token diagnostic, but they do **not** by themselves authenticate every MCP protocol request. Before exposing this endpoint to untrusted users or real data, add authentication middleware at the HTTP layer or use a trusted gateway, and test it. Do not connect production systems.

## Deploy as a separate service

Streamlit Community Cloud hosts the dashboard, not this standalone MCP service. The MCP server must be deployed separately.

A Render free web service is one possible learning target if available for your account. Free instances can sleep after inactivity and service terms may change; confirm the current plan and limits before relying on it.

1. Push `mcp_server.py`, `requirements-mcp.txt`, `render.yaml`, `core_tools.py`, `data/`, and `knowledge/` to the same GitHub repository.
2. Open the Render dashboard and create a new Web Service from the repository.
3. If Render detects `render.yaml`, review the proposed service settings.
4. Confirm build command: `pip install -r requirements-mcp.txt`.
5. Confirm start command: `python mcp_server.py`.
6. Set `MCP_API_TOKEN` to a long random secret in the service environment.
7. Deploy.
8. Open `https://YOUR-SERVICE.onrender.com/health`. Expected JSON includes `"status":"ok"`.
9. The MCP endpoint is normally `https://YOUR-SERVICE.onrender.com/mcp`.

## Do not connect n8n yet

First verify the service deploys and the health route works. Then we will validate MCP tool discovery using a compatible MCP client. After that, we will configure n8n and decide the safest supported authentication path.

## Note about public endpoint authentication

This starter exposes only synthetic-data tools. The `MCP_API_TOKEN` variable is not yet enforced on the MCP `/mcp` route. Treat the URL as a demo endpoint and do not use sensitive data. Before connecting it to broader access, we will add and verify authentication middleware supported by the selected SDK version/hosting arrangement.
