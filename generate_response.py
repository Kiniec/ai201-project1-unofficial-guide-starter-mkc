"""
generate_response.py  —  Milestone 5
Full RAG pipeline: retrieve → format context → generate → return answer + sources.

Usage
-----
Interactive CLI:
    python generate_response.py

Single question:
    python generate_response.py --question "Where can I get food near UT Dallas?"
"""

import argparse
import os
import re
from dotenv import load_dotenv
from groq import Groq

from embed_and_retrieve import retrieve, TOP_K

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MODEL         = "llama-3.3-70b-versatile"
TEMPERATURE   = 0.2   # low — we want factual, grounded answers

SYSTEM_PROMPT = (
    "You are a compassionate and knowledgeable guide helping college students "
    "in the Dallas area who are facing housing insecurity or food insecurity. "
    "Answer the question using only the information in the provided documents. "
    "If the documents don't contain enough information to answer, say "
    "'I don't have enough information on that.' "
    "When you use information from a document, cite it by its source name. "
    "At the end of your answer, list every source you drew from under a "
    "'Sources:' heading, formatted as '- Source Name: URL'."
)


# ── Query enrichment ─────────────────────────────────────────────────────────
# When a question names a specific org AND asks about operational details
# (hours, days, intake, requirements), the org name + key terms are prepended
# to the retrieval query. Tested: lifts correct Dallas Life chunk from rank 7
# to rank 1 without degrading other evaluation questions.

_ORG_EXPANSIONS: dict[str, list[str]] = {
    # Only enrich orgs where vanilla retrieval was confirmed failing.
    # Tested: Dallas Life intake chunks sit at rank 7 without enrichment,
    # rank 1 with it. All other orgs retrieved correctly without enrichment.
    "dallas life": ["dallas life", "shelter", "intake"],
    "dallaslife":  ["dallas life", "shelter", "intake"],
}

_INTENT_TERMS: list[tuple[list[str], list[str]]] = [
    (["hour", "open", "time", "when"],        ["hours", "schedule"]),
    (["day", "days", "schedule", "when"],     ["hours", "schedule", "monday", "friday"]),
    (["intake", "check in", "arrive"],        ["intake", "walk-up"]),
    (["require", "need", "bring", "id"],      ["requirements", "documents"]),
    (["eligible", "qualify", "apply"],        ["eligibility", "apply"]),
    (["food", "eat", "pantry", "meal"],       ["food", "pantry"]),
    (["shelter", "sleep", "stay", "housing"], ["shelter", "housing"]),
]


def _enrich_query(question: str) -> str:
    """
    Return a retrieval-optimized query when the question targets a specific
    known organization. Falls back to the original question otherwise.
    """
    q = question.lower()

    org_terms: list[str] = []
    for alias, expansion in _ORG_EXPANSIONS.items():
        if alias in q:
            org_terms = expansion
            break

    if not org_terms:
        return question

    intent_extras: list[str] = []
    for triggers, extras in _INTENT_TERMS:
        if any(t in q for t in triggers):
            intent_extras.extend(extras)

    if not intent_extras:
        return question  # org present but no specific intent — don't over-enrich

    return " ".join(org_terms + intent_extras)


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(hits: list[dict]) -> str:
    """Format retrieved chunks as a numbered document block for the prompt."""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(
            f"[Document {i}]\n"
            f"Source: {h['source']}\n"
            f"URL: {h['url']}\n"
            f"---\n"
            f"{h['text']}"
        )
    return "\n\n".join(parts)


def _dedupe_sources(hits: list[dict]) -> list[dict]:
    """Return one entry per unique source (name + url), preserving rank order."""
    seen = set()
    sources = []
    for h in hits:
        key = h["source"]
        if key not in seen:
            seen.add(key)
            sources.append({"source": h["source"], "url": h["url"]})
    return sources


# ── Pipeline ──────────────────────────────────────────────────────────────────

def generate_response(question: str, k: int = TOP_K) -> dict:
    """
    Full RAG pipeline for one question.

    Returns
    -------
    dict with keys:
        answer   — the model's grounded answer
        sources  — list of {source, url} dicts actually retrieved
        question — the original question (for display)
    """
    # 1. Retrieve (enrich query when question targets a specific known org)
    retrieval_query = _enrich_query(question)
    hits = retrieve(retrieval_query, k=k)

    # 2. Build prompt
    context = _build_context(hits)
    user_message = (
        f"Documents:\n\n{context}\n\n"
        f"Question: {question}"
    )

    # 3. Call Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Strip the model's own "Sources:" block — the pipeline renders sources itself
    answer = re.sub(r"\n+Sources:.*", "", raw, flags=re.DOTALL).strip()
    sources = _dedupe_sources(hits)

    return {
        "question": question,
        "answer":   answer,
        "sources":  sources,
    }


# ── Display ───────────────────────────────────────────────────────────────────

def _print_result(result: dict) -> None:
    print(f"\n{'─'*62}")
    print(f"Q: {result['question']}")
    print(f"{'─'*62}")
    print(result["answer"])
    print(f"\nSources:")
    for s in result["sources"]:
        print(f"  - {s['source']}: {s['url']}")
    print(f"{'─'*62}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str, default="",
                        help="Single question to answer")
    args = parser.parse_args()

    if args.question:
        result = generate_response(args.question)
        _print_result(result)
        return

    # Interactive loop
    print("Unofficial Housing & Food Guide — Dallas Area")
    print("Type your question and press Enter. Type 'quit' to exit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break
        result = generate_response(question)
        _print_result(result)


if __name__ == "__main__":
    main()
