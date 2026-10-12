"""Standalone MCP server exposing safe NEXUS demo tools.

This server must run as a separate service for remote MCP connectivity.
It is not launched automatically by Streamlit Community Cloud.
"""

from mcp.server.fastmcp import FastMCP
from core_tools import retrieve_knowledge, load_incidents, analyze_incident, generate_incident_report

mcp = FastMCP("NEXUS AI Automation Hub")

@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """Search the local synthetic NEXUS knowledge documents."""
    return retrieve_knowledge(query, top_k=top_k)

@mcp.tool()
def list_synthetic_incidents() -> list[dict]:
    """Return the synthetic incident register; no production systems are accessed."""
    return load_incidents().to_dict(orient="records")

@mcp.tool()
def analyze_synthetic_incident(incident_id: str) -> dict:
    """Analyze a selected synthetic incident using deterministic rules."""
    incidents = load_incidents()
    match = incidents[incidents["incident_id"].astype(str) == str(incident_id)]
    if match.empty:
        return {"error": f"Unknown synthetic incident ID: {incident_id}"}
    return analyze_incident(match.iloc[0].to_dict())

@mcp.tool()
def create_simulated_incident_report(incident_id: str) -> str:
    """Create a report from synthetic data; this tool does not send or execute actions."""
    incidents = load_incidents()
    match = incidents[incidents["incident_id"].astype(str) == str(incident_id)]
    if match.empty:
        return f"Unknown synthetic incident ID: {incident_id}"
    return generate_incident_report(match.iloc[0].to_dict())

if __name__ == "__main__":
    # Streamable HTTP transport for a separately hosted MCP endpoint.
    mcp.run(transport="streamable-http")
