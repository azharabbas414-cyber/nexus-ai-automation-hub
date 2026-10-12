import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

type Env = { MCP_API_TOKEN?: string };

const INCIDENTS = [
  {
    "incident_id": "NX-1001",
    "category": "Cybersecurity",
    "title": "Suspicious login from unusual location",
    "priority": "High",
    "status": "Open",
    "region": "North",
    "affected_service": "Identity Demo",
    "description": "Simulated sign-in alert for training only"
  },
  {
    "incident_id": "NX-1002",
    "category": "Telecom",
    "title": "BGP peer session flapping",
    "priority": "Critical",
    "status": "Investigating",
    "region": "Central",
    "affected_service": "IP Core Demo",
    "description": "Synthetic BGP event; no real router was queried"
  },
  {
    "incident_id": "NX-1003",
    "category": "Business",
    "title": "Unexpected billing variance",
    "priority": "Medium",
    "status": "Open",
    "region": "South",
    "affected_service": "Billing Demo",
    "description": "Synthetic variance in a sample billing dataset"
  },
  {
    "incident_id": "NX-1004",
    "category": "Cybersecurity",
    "title": "Potential phishing email reported",
    "priority": "Medium",
    "status": "Closed",
    "region": "North",
    "affected_service": "Email Demo",
    "description": "Training example; no email system was accessed"
  },
  {
    "incident_id": "NX-1005",
    "category": "Telecom",
    "title": "Elevated simulated packet loss",
    "priority": "High",
    "status": "Open",
    "region": "East",
    "affected_service": "Transport Demo",
    "description": "Generated sample event for dashboard testing"
  },
  {
    "incident_id": "NX-1006",
    "category": "Business",
    "title": "Missing region values in report",
    "priority": "Low",
    "status": "Closed",
    "region": "Central",
    "affected_service": "Analytics Demo",
    "description": "Synthetic data-quality issue for demonstration"
  }
];
const KNOWLEDGE = [
  {
    "title": "Cybersecurity Incident Triage Runbook",
    "source": "cybersecurity_runbook.md",
    "content": "# Cybersecurity Incident Triage Runbook\n\nFor simulated security alerts, validate alert context, record timestamps, preserve relevant evidence, and escalate according to an approved response process. Do not isolate hosts, disable accounts, or change security controls without authorization and explicit approval.\n\nKeywords: cybersecurity, incident, phishing, containment, alert."
  },
  {
    "title": "Business Data Quality Runbook",
    "source": "data_quality_runbook.md",
    "content": "# Business Data Quality Runbook\n\nFor a suspected anomaly, verify the dataset source, schema, row count, null values, duplicates, and plausible ranges. Separate confirmed findings from hypotheses and document assumptions. Do not overwrite source data during analysis.\n\nKeywords: data, anomaly, validation, business, outliers."
  },
  {
    "title": "Network Incident Triage Runbook",
    "source": "network_runbook.md",
    "content": "# Network Incident Triage Runbook\n\nFor a reported BGP or service incident, establish the affected service, region, time window, and customer impact. Use approved read-only monitoring and documented checks. Compare observations with recent changes and known events. Escalate to an authorized engineer; do not modify router configuration as part of this demo.\n\nKeywords: BGP, network, router, service, packet loss."
  }
];

function asText(value: unknown): string {
  return typeof value === "string" ? value : String(value ?? "");
}

function scoreDocument(query: string, doc: { title: string; content: string }): number {
  const terms = [...new Set(query.toLowerCase().split(/[^a-z0-9]+/).filter((word) => word.length > 2))];
  const haystack = `${doc.title} ${doc.content}`.toLowerCase();
  return terms.reduce((score, term) => score + (haystack.includes(term) ? 1 : 0), 0);
}
