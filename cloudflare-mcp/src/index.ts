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

function createServer() {
  const server = new McpServer({
    name: "nexus-ai-automation-hub",
    version: "1.0.0",
  });

  server.registerTool(
    "list_incidents",
    {
      description: "List synthetic NEXUS AI demo incidents. Optional filters: category, priority, status, and region.",
      inputSchema: {
        category: z.string().optional().describe("Optional category, e.g. Telecom or Cybersecurity"),
        priority: z.string().optional().describe("Optional priority, e.g. Critical, High, Medium, Low"),
        status: z.string().optional().describe("Optional status, e.g. Open, Investigating, Closed"),
        region: z.string().optional().describe("Optional region"),
      },
    },
    async ({ category, priority, status, region }) => {
      const rows = INCIDENTS.filter((item) =>
        (!category || item.category.toLowerCase() === category.toLowerCase()) &&
        (!priority || item.priority.toLowerCase() === priority.toLowerCase()) &&
        (!status || item.status.toLowerCase() === status.toLowerCase()) &&
        (!region || item.region.toLowerCase() === region.toLowerCase())
      );
      return { content: [{ type: "text", text: JSON.stringify({ count: rows.length, incidents: rows, data_notice: "Synthetic demonstration data only; no live systems were queried." }, null, 2) }] };
    }
  );

  server.registerTool(
    "analyze_incident",
    {
      description: "Return deterministic triage guidance for one synthetic incident ID.",
      inputSchema: { incident_id: z.string().describe("Incident ID, for example NX-1002") },
    },
    async ({ incident_id }) => {
      const incident = INCIDENTS.find((item) => item.incident_id.toLowerCase() === incident_id.trim().toLowerCase());
      if (!incident) return { content: [{ type: "text", text: `Incident ${incident_id} was not found in the synthetic demo dataset.` }], isError: true };
      const urgent = ["critical", "high"].includes(incident.priority.toLowerCase());
      const result = {
        incident_id: incident.incident_id,
        classification: incident.category,
        priority: incident.priority,
        status: incident.status,
        region: incident.region,
        affected_service: incident.affected_service,
        review_level: urgent ? "Urgent review recommended" : "Standard review",
        evidence: incident.description,
        recommended_next_step: incident.category === "Telecom"
          ? "Establish affected service, region, time window, and customer impact. Use approved read-only checks and escalate to an authorized engineer."
          : incident.category === "Cybersecurity"
          ? "Validate alert context, record timestamps, preserve relevant evidence, and escalate through the approved response process."
          : "Verify source, schema, row count, null values, duplicates, and plausible ranges; document assumptions.",
        safety_note: "Synthetic example only. No real system was queried or changed. Do not take action without authorization.",
      };
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.registerTool(
    "generate_incident_report",
    {
      description: "Generate a plain-text report for one synthetic incident.",
      inputSchema: { incident_id: z.string().describe("Incident ID, for example NX-1002") },
    },
    async ({ incident_id }) => {
      const incident = INCIDENTS.find((item) => item.incident_id.toLowerCase() === incident_id.trim().toLowerCase());
      if (!incident) return { content: [{ type: "text", text: `Incident ${incident_id} was not found in the synthetic demo dataset.` }], isError: true };
      const urgent = ["critical", "high"].includes(incident.priority.toLowerCase());
      const report = [
        "NEXUS AI — SIMULATED INCIDENT REPORT",
        `Incident: ${incident.incident_id}`,
        `Category: ${incident.category}`,
        `Title: ${incident.title}`,
        `Priority: ${incident.priority}`,
        `Status: ${incident.status}`,
        `Region: ${incident.region}`,
        `Affected service: ${incident.affected_service}`,
        `Description: ${incident.description}`,
        `Review level: ${urgent ? "Urgent review recommended" : "Standard review"}`,
        "Recommended next step: Review the supplied synthetic evidence and follow the relevant runbook.",
        "Safety: Synthetic example only; no real system was queried or changed.",
      ].join("\n");
      return { content: [{ type: "text", text: report }] };
    }
  );

  server.registerTool(
    "search_knowledge",
    {
      description: "Search the three embedded NEXUS demo runbooks using deterministic keyword matching.",
      inputSchema: {
        query: z.string().describe("Search phrase, e.g. BGP, phishing, data quality"),
        top_k: z.number().int().min(1).max(3).optional().describe("Maximum documents to return, 1 to 3; defaults to 3"),
      },
    },
    async ({ query, top_k }) => {
      const cleanQuery = query.trim();
      if (!cleanQuery) return { content: [{ type: "text", text: "Please provide a non-empty search query." }], isError: true };
      const ranked = KNOWLEDGE
        .map((doc) => ({ ...doc, score: scoreDocument(cleanQuery, doc) }))
        .filter((doc) => doc.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, top_k ?? 3);
      return { content: [{ type: "text", text: JSON.stringify({
        query: cleanQuery,
        retrieval_method: "Deterministic keyword overlap; this is not an embedding-based vector search.",
        count: ranked.length,
        documents: ranked,
      }, null, 2) }] };
    }
  );

  return server;
}

function tokenMatches(provided: string, expected: string): boolean {
  // Compare all characters without early exit to avoid a simple timing shortcut.
  let difference = provided.length ^ expected.length;
  const maxLength = Math.max(provided.length, expected.length);
  for (let i = 0; i < maxLength; i++) {
    difference |= (provided.charCodeAt(i) || 0) ^ (expected.charCodeAt(i) || 0);
  }
  return difference === 0;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({ status: "ok", service: "nexus-ai-mcp", data_mode: "synthetic-demo" });
    }

    if (url.pathname !== "/mcp") {
      return new Response("Not found", { status: 404 });
    }

    if (!env.MCP_API_TOKEN) {
      return Response.json({ error: "MCP_API_TOKEN secret is not configured." }, { status: 503 });
    }

    const authorization = request.headers.get("Authorization") || "";
    const prefix = "Bearer ";
    const provided = authorization.startsWith(prefix) ? authorization.slice(prefix.length) : "";
    if (!provided || !tokenMatches(provided, env.MCP_API_TOKEN)) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    return createMcpHandler(createServer)(request, env, ctx);
  },
};
