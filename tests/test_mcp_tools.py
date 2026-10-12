"""Basic tests for the shared deterministic tools used by the MCP server."""

import unittest
from core_tools import (
    load_incidents,
    retrieve_knowledge,
    analyze_incident,
    generate_incident_report,
)


class MCPToolDataTests(unittest.TestCase):
    def test_incidents_exist(self):
        self.assertGreaterEqual(len(load_incidents()), 1)

    def test_knowledge_search(self):
        results = retrieve_knowledge("BGP network router", top_k=3)
        self.assertTrue(results)
        self.assertIn("network_runbook.md", [item["source"] for item in results])

    def test_unknown_incident_is_handled_by_caller_contract(self):
        ids = set(load_incidents()["incident_id"].astype(str))
        self.assertNotIn("NX-NOT-REAL", ids)

    def test_report_is_simulated(self):
        incident = load_incidents().iloc[0].to_dict()
        report = generate_incident_report(incident)
        self.assertIn("SIMULATED INCIDENT REPORT", report)
        self.assertIn("Synthetic example only", report)


if __name__ == "__main__":
    unittest.main()
