"""
Source Priority Registry
Defines reliability tiers for all knowledge sources.

Priority (lower number = higher authority):
  1 - Signed customer agreements (override everything)
  2 - Current policy / SOP documents
  3 - Product operations guide
  9 - Historical tickets (context only, may be WRONG)
  NEVER - Deprecated documents
"""

SOURCE_REGISTRY = {
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {
        "priority": 1,
        "label": "Northstar Enterprise Agreement",
        "status": "ACTIVE",
        "applies_to": ["ACCT-001"],
        "description": "Signed enterprise agreement. Overrides all default policies for Northstar.",
    },
    "06_LumenWorks_Service_Agreement.pdf": {
        "priority": 1,
        "label": "LumenWorks Service Agreement",
        "status": "ACTIVE",
        "applies_to": ["ACCT-002"],
        "description": "Signed service agreement. Overrides default policies for LumenWorks.",
    },
    "01_Support_Policy_v3_CURRENT.pdf": {
        "priority": 2,
        "label": "Support Policy v3 (Current)",
        "status": "CURRENT",
        "applies_to": ["ALL"],
        "description": "Current support policy. Effective 1 May 2026.",
    },
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": {
        "priority": 2,
        "label": "Cancellation & Service Credit SOP v4 (Current)",
        "status": "CURRENT",
        "applies_to": ["ALL"],
        "description": "Current SOP for cancellations and service credits. Effective 15 June 2026.",
    },
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {
        "priority": 3,
        "label": "Product Operations Guide (Current)",
        "status": "CURRENT",
        "applies_to": ["ALL"],
        "description": "Product capabilities and known issues. Updated 14 August 2026.",
    },
    "02_Support_Policy_v2_DEPRECATED.pdf": {
        "priority": 99,
        "label": "Support Policy v2 (DEPRECATED - DO NOT USE)",
        "status": "DEPRECATED",
        "applies_to": [],
        "description": "DEPRECATED. Superseded by v3. Must never be used for answering current questions.",
    },
    "historical_ticket": {
        "priority": 9,
        "label": "Historical Ticket (Context Only)",
        "status": "CONTEXT_ONLY",
        "applies_to": [],
        "description": "Historical ticket resolutions. May contain incorrect guidance. Use as context only.",
    },
}

KNOWN_WRONG_RESOLUTIONS = {
    "TKT-450": {
        "wrong_claim": "INR 250 cancellation fee applies to Northstar after 30 minutes",
        "correction": "Northstar Enterprise Agreement waives cancellation fees for all BOOKED orders before pickup.",
        "correct_source": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    },
    "TKT-451": {
        "wrong_claim": "Growth plan only supports 3,000 rows in bulk upload",
        "correction": "Product limit is 5,000 rows. Current failures >3,000 rows are due to bug KI-208, not a plan restriction.",
        "correct_source": "04_Product_Operations_Guide_and_Known_Issues.pdf",
    },
}


def get_source_info(filename: str) -> dict:
    return SOURCE_REGISTRY.get(filename, {
        "priority": 5,
        "label": filename,
        "status": "UNKNOWN",
        "applies_to": ["ALL"],
        "description": "Unknown source.",
    })


def get_priority_label(priority: int) -> str:
    if priority == 1:
        return "🔴 Customer Agreement (Highest Authority)"
    elif priority == 2:
        return "🟡 Current Policy/SOP"
    elif priority == 3:
        return "🟢 Product Guide"
    elif priority == 9:
        return "⚠️ Historical Ticket (May Be Incorrect)"
    elif priority == 99:
        return "🚫 DEPRECATED — Do Not Use"
    return "❓ Unknown"


def detect_conflict(sources_used: list[str], account_id: str | None = None) -> dict | None:
    """Detect if multiple sources with different priorities give potentially conflicting info."""
    relevant = []
    for s in sources_used:
        info = get_source_info(s)
        # Skip deprecated and historical for conflict detection
        if info["priority"] in (9, 99):
            continue
        if info["applies_to"] == ["ALL"] or (account_id and account_id in info.get("applies_to", [])):
            relevant.append((s, info["priority"]))

    priorities = [p for _, p in relevant]
    if len(set(priorities)) > 1 and 1 in priorities:
        return {
            "conflict": True,
            "message": "A signed customer agreement overrides the general policy. The agreement takes precedence.",
            "sources": relevant,
        }
    return None
