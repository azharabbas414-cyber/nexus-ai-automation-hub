"""NEXUS AI Automation Hub — authenticated remote MCP server.

All tools use local synthetic data and deterministic project logic.
No live routers, production accounts, or external business systems are accessed.

Set MCP_API_TOKEN as a secret in the hosting provider. Every HTTP route except
/health requires Authorization: Bearer <MCP_API_TOKEN>. The /health endpoint is
public only so Render can check service health; it exposes no sensitive data.
"""

import hmac
import os
from typing import Any

import uvicorn
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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


class BearerTokenMiddleware:
    """Require a configured bearer token on all HTTP paths except /health."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        # Pass lifespan events through unchanged so the MCP SDK can start/stop
        # its session manager correctly.
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/health":
            await self.app(scope, receive, send)
            return

        # Fail closed if the secret has not been configured in Render.
        if not self.token:
            response = JSONResponse(
                {
                    "error": "server_misconfigured",
                    "message": "MCP_API_TOKEN is not configured.",
                },
                status_code=503,
            )
            await response(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get(b"authorization", b"").decode(
            "latin-1", errors="ignore"
        )
        expected = f"Bearer {self.token}"

        if not hmac.compare_digest(authorization, expected):
            response = JSONResponse(
                {"error": "unauthorized", "message": "Valid bearer token required."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


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
    """Public health endpoint for Render; it reveals no secrets or dataset contents."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "nexus-mcp",
            "mode": "synthetic-data-only",
        }
    )


# The middleware wraps the complete MCP HTTP application, so /mcp requests
# are authenticated before the SDK parses or dispatches any tool call.
app = BearerTokenMiddleware(mcp.streamable_http_app(), API_TOKEN)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
