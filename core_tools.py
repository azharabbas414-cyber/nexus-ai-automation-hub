"""Reusable deterministic tools shared by Streamlit and the MCP server."""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "sample_data" / "incidents.csv"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def load_incidents() -> pd.DataFrame:
    columns = ["incident_id", "category", "title", "priority", "status", "region", "affected_service", "description"]
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(DATA_PATH).fillna("")
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def load_documents() -> list[dict]:
    docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        content = path.read_text(encoding="utf-8")
        first_heading = next((line.strip("# ").strip() for line in content.splitlines() if line.startswith("# ")), path.stem)
        docs.append({"title": first_heading, "source": path.name, "content": content})
    return docs


def retrieve_knowledge(query: str, top_k: int = 3) -> list[dict]:
    """Small local RAG baseline using TF-IDF retrieval; no external vector database."""
    docs = load_documents()
    if not docs:
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    query = (query or "").strip()
    if not query:
        return docs[:max(1, top_k)]
    corpus = [f"{d['title']}\n{d['content']}" for d in docs]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    ranked = sorted(zip(scores, docs), key=lambda item: item[0], reverse=True)
    return [
        {**doc, "score": round(float(score), 4)}
        for score, doc in ranked[:max(1, top_k)]
        if score > 0
    ]


def analyze_incident(incident: dict) -> dict:
    """Deterministic analysis of synthetic data, not an AI-generated finding."""
    priority = str(incident.get("priority", "Unknown")).lower()
    severity = "urgent review recommended" if priority in {"critical", "high"} else "standard review"
    return {
        "incident_id": str(incident.get("incident_id", "unknown")),
        "classification": incident.get("category", "Unclassified"),
        "priority": incident.get("priority", "Unknown"),
        "status": incident.get("status", "Unknown"),
        "review_level": severity,
        "evidence": incident.get("description", ""),
        "safety_note": "Synthetic example only; no real system was queried or changed.",
    }


def generate_incident_report(incident: dict) -> str:
    analysis = analyze_incident(incident)
    return (
        f"NEXUS AI — SIMULATED INCIDENT REPORT\n"
        f"Incident: {analysis['incident_id']}\n"
        f"Category: {analysis['classification']}\n"
        f"Priority: {analysis['priority']}\n"
        f"Status: {analysis['status']}\n"
        f"Review level: {analysis['review_level']}\n"
        f"Description: {analysis['evidence']}\n"
        f"Recommended next step: Review the supplied synthetic evidence and follow the relevant runbook.\n"
        f"Safety: {analysis['safety_note']}\n"
    )
