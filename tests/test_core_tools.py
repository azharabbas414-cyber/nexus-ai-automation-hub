import unittest
from core_tools import load_incidents, retrieve_knowledge, analyze_incident, generate_incident_report

class CoreToolTests(unittest.TestCase):
    def test_sample_incidents_load(self):
        self.assertGreaterEqual(len(load_incidents()), 1)

    def test_rag_retrieves_network_document(self):
        docs = retrieve_knowledge("BGP router network", top_k=3)
        self.assertTrue(docs)
        self.assertIn("network_runbook.md", [d["source"] for d in docs])

    def test_incident_analysis_is_simulated(self):
        row = load_incidents().iloc[0].to_dict()
        result = analyze_incident(row)
        self.assertIn("Synthetic example only", result["safety_note"])

    def test_report_has_safety_note(self):
        row = load_incidents().iloc[0].to_dict()
        self.assertIn("SIMULATED INCIDENT REPORT", generate_incident_report(row))

if __name__ == "__main__":
    unittest.main()
