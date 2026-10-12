# NEXUS AI MCP Worker (Cloudflare)

This is a separate Cloudflare Worker implementation. It does not replace or modify the existing Python/Streamlit application.

## Endpoints
- `GET /health` — public health check.
- `/mcp` — authenticated MCP Streamable HTTP endpoint. Requires `Authorization: Bearer <MCP_API_TOKEN>`.

## Tools
- `list_incidents`
- `analyze_incident`
- `generate_incident_report`
- `search_knowledge`

## Safety and data notes
- The incidents are the six synthetic records from `data/sample_data/incidents.csv`.
- The three supplied Markdown runbooks are embedded in `src/index.ts`.
- Knowledge retrieval uses deterministic keyword overlap, not TF-IDF or embeddings.
- This worker does not query routers, mail systems, accounts, billing platforms, or any live infrastructure.
- Set `MCP_API_TOKEN` as a Cloudflare Worker secret. Never put the token in GitHub source files.

## Cloudflare Git integration
Run from this folder:
- Build command: `cd cloudflare-mcp && npm install`
- Deploy command: `cd cloudflare-mcp && npx wrangler deploy`

Set `MCP_API_TOKEN` in Worker Settings > Variables and Secrets as a Secret.
