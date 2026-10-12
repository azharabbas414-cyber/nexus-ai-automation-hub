"""NEXUS AI Automation Hub — remote MCP server.

Exposes safe tools over Streamable HTTP. All operations use synthetic local data.
No live routers, production accounts, or external business systems are accessed.

Hosting note:
- Deploy this as a separate Python web service, not as part of Streamlit Community Cloud.
- Configure MCP_API_TOKEN in the hosting provider's environment/secrets.
- The token check protects tool calls with a simple Bearer token at the HTTP layer.
"""

import hmac
import os
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP
from core_tools import (
    retrieve_knowledge,
    load_incidents,
    analyze_incident,
    generate_incident_report,
)

SERVER_NAME = "NEXUS AI Automation Hub MCP"
API_TOKEN = os.getenv("MCP_API_TOKEN", "").strip()

mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """Search NEXUS's local synthetic runbooks for relevant troubleshooting guidance."""
    safe_top_k = max(1, min(int(top_k), 5))
    return retrieve_knowledge(query=query, top_k=safe_top_k)


@mcp.tool()
def list_synthetic_incidents() -> list[dict]:
    """List the sample incident register. All records are synthetic training data."""
    return load_incidents().to_dict(orient="records")


@mcp.tool()
def analyze_synthetic_incident(incident_id: str) -> dict:
    """Classify and summarize a synthetic incident using deterministic rules."""
    incidents = load_incidents()
    matched = incidents[incidents["incident_id"].astype(str) == str(incident_id).strip()]
    if matched.empty:
        return {
            "error": "incident_not_found",
            "message": f"No synthetic incident found with ID {incident_id!r}.",
        }
    return analyze_incident(matched.iloc[0].to_dict())


@mcp.tool()
def create_simulated_incident_report(incident_id: str) -> str:
    """Create report text from a synthetic incident; it does not send or execute actions."""
    incidents = load_incidents()
    matched = incidents[incidents["incident_id"].astype(str) == str(incident_id).strip()]
    if matched.empty:
        return f"Cannot create report: unknown synthetic incident ID {incident_id!r}."
    return generate_incident_report(matched.iloc[0].to_dict())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health endpoint for hosting-provider health checks."""
    return JSONResponse({
        "status": "ok",
        "service": "nexus-mcp",
        "mode": "synthetic-data-only",
    })


@mcp.custom_route("/authorize", methods=["GET"])
async def authorization_check(request: Request) -> JSONResponse:
    """Safe diagnostic endpoint to check whether a bearer token was supplied."""
    if not API_TOKEN:
        return JSONResponse(
            {"status": "not_configured", "message": "MCP_API_TOKEN is not set."},
            status_code=503,
        )
    supplied = request.headers.get("authorization", "")
    expected = f"Bearer {API_TOKEN}"
    if not hmac.compare_digest(supplied, expected):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    return JSONResponse({"status": "authorized"})


if __name__ == "__main__":
    # MCP endpoint defaults to /mcp with the Streamable HTTP transport.
    # The host platform should provide HTTPS at the public edge.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
