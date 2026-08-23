"""
Tool 1: Document Search
Performs semantic RAG over all PDF documents.
Respects source priority and filters deprecated content.
"""

from rag.retriever import search, format_for_prompt
from agent.source_registry import KNOWN_WRONG_RESOLUTIONS


def doc_search(query: str, account_id: str | None = None, top_k: int = 6) -> dict:
    """
    Search policy documents, agreements, and SOPs.

    Returns structured result with sources, priority info, and any conflict warnings.
    """
    results = search(query, top_k=top_k, account_id=account_id, include_deprecated=False)

    # Check if any known wrong resolutions are relevant
    wrong_flags = []
    for ticket_id, info in KNOWN_WRONG_RESOLUTIONS.items():
        if any(kw in query.lower() for kw in ["cancel", "fee", "bulk upload", "csv", "row"]):
            wrong_flags.append({
                "ticket": ticket_id,
                "warning": f"⚠️ Historical ticket {ticket_id} contains an incorrect resolution: {info['wrong_claim']}. "
                           f"Correct answer: {info['correction']} (per {info['correct_source']})"
            })

    sources_used = list(set(r["source"] for r in results))
    formatted = format_for_prompt(results)

    return {
        "tool": "doc_search",
        "query": query,
        "results": results,
        "sources_used": sources_used,
        "formatted_context": formatted,
        "historical_warnings": wrong_flags,
        "num_results": len(results),
    }
