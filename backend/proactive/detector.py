"""
Proactive Issue Detector (Bonus Problem 1)
Analyzes tickets and orders to surface recurring, urgent, or unusual issues
for internal operations staff — without waiting for someone to ask.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./db/parcelPilot.db")

DATASET_SNAPSHOT = datetime(2026, 8, 16, 11, 0, 0)

# SLA response targets in minutes (from Support Policy v3 + customer agreements)
SLA_TARGETS = {
    "ACCT-001": {"P1": 15, "P2": 60, "P3": 480},      # Northstar: custom 15min P1
    "ACCT-002": {"P1": 120, "P2": 240, "P3": 2880},    # LumenWorks: 2 biz hours P1
    "ACCT-003": {"P1": 240, "P2": 480, "P3": 2880},    # Beacon: Standard
    "ACCT-004": {"P1": 30, "P2": 120, "P3": 480},      # Axis Labs: Enterprise
    "DEFAULT":  {"P1": 30, "P2": 120, "P3": 480},
}

# Keyword clusters for pattern detection
ISSUE_PATTERNS = {
    "bulk_upload": ["bulk upload", "csv", "import", "upload fail", "rows"],
    "pickup_delay": ["pickup", "late", "carrier", "not picked", "still booked", "booked after"],
    "cancellation": ["cancel", "cancellation", "fee", "refund"],
    "api_security": ["api key", "credential", "exposure", "security", "token"],
    "status_sync": ["still shows", "status", "webhook", "booked", "not updated"],
    "shipment_creation": ["shipment creation", "http 500", "failing", "error creating"],
    "billing": ["billing", "invoice", "payment", "charge"],
}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def classify_ticket_priority(ticket: dict) -> str:
    """Classify a ticket's P-level based on subject/description."""
    text = (ticket.get("subject", "") + " " + ticket.get("description", "")).lower()

    p1_keywords = ["outage", "down", "all failing", "http 500", "production", "api key", "security",
                   "credential", "exposure", "every user", "no workaround"]
    p2_keywords = ["major", "bulk", "feature unavailable", "bulk upload", "workaround"]

    for kw in p1_keywords:
        if kw in text:
            return "P1"
    for kw in p2_keywords:
        if kw in text:
            return "P2"
    return "P3"


def get_sla_status(ticket: dict) -> dict:
    """Check if a ticket has breached its SLA."""
    account_id = ticket.get("account_id", "DEFAULT")
    priority = classify_ticket_priority(ticket)
    sla_minutes = SLA_TARGETS.get(account_id, SLA_TARGETS["DEFAULT"])[priority]

    created_at_str = ticket.get("created_at", "")
    try:
        created_at = datetime.fromisoformat(created_at_str)
        elapsed_minutes = (DATASET_SNAPSHOT - created_at).total_seconds() / 60
        target_minutes = sla_minutes
        breached = elapsed_minutes > target_minutes
        approaching = not breached and elapsed_minutes > target_minutes * 0.8

        return {
            "priority": priority,
            "sla_target_minutes": target_minutes,
            "elapsed_minutes": round(elapsed_minutes),
            "breached": breached,
            "approaching": approaching,
            "status": "BREACHED" if breached else ("APPROACHING" if approaching else "OK"),
        }
    except Exception:
        return {"priority": priority, "sla_target_minutes": sla_minutes,
                "elapsed_minutes": None, "breached": False, "approaching": False, "status": "UNKNOWN"}


def detect_issue_clusters(tickets: list[dict]) -> list[dict]:
    """Group tickets by detected issue pattern."""
    clusters = {}
    for ticket in tickets:
        text = (ticket.get("subject", "") + " " + ticket.get("description", "")).lower()
        for pattern, keywords in ISSUE_PATTERNS.items():
            if any(kw in text for kw in keywords):
                if pattern not in clusters:
                    clusters[pattern] = []
                clusters[pattern].append(ticket)

    result = []
    for pattern, matched_tickets in clusters.items():
        if len(matched_tickets) >= 1:
            account_ids = list(set(t["account_id"] for t in matched_tickets))
            result.append({
                "pattern": pattern,
                "pattern_label": pattern.replace("_", " ").title(),
                "ticket_count": len(matched_tickets),
                "tickets": [t["ticket_id"] for t in matched_tickets],
                "accounts_affected": account_ids,
                "multi_customer": len(account_ids) > 1,
                "severity": "HIGH" if len(matched_tickets) >= 2 or len(account_ids) > 1 else "MEDIUM",
            })

    result.sort(key=lambda x: (-x["ticket_count"], x["pattern"]))
    return result


def get_proactive_insights() -> dict:
    """
    Main entry point: runs all detectors and returns a structured insights report.
    """
    with _conn() as conn:
        open_tickets = [dict(r) for r in conn.execute(
            "SELECT t.*, a.account_name, a.plan FROM tickets t "
            "JOIN accounts a ON t.account_id = a.account_id "
            "WHERE t.status = 'open'"
        ).fetchall()]

        all_orders = [dict(r) for r in conn.execute(
            "SELECT o.*, a.account_name FROM orders o "
            "JOIN accounts a ON o.account_id = a.account_id"
        ).fetchall()]

    # 1. SLA status for each open ticket
    sla_alerts = []
    for ticket in open_tickets:
        sla = get_sla_status(ticket)
        if sla["breached"] or sla["approaching"]:
            sla_alerts.append({
                "ticket_id": ticket["ticket_id"],
                "account_id": ticket["account_id"],
                "account_name": ticket.get("account_name"),
                "subject": ticket["subject"],
                "assigned_to": ticket.get("assigned_to"),
                **sla,
            })
    sla_alerts.sort(key=lambda x: (0 if x["breached"] else 1, x.get("elapsed_minutes", 0) * -1))

    # 2. Account surge: multiple open tickets from same account
    account_ticket_counts = {}
    for t in open_tickets:
        aid = t["account_id"]
        account_ticket_counts[aid] = account_ticket_counts.get(aid, 0) + 1

    surge_alerts = []
    for aid, count in account_ticket_counts.items():
        if count >= 2:
            account_tickets = [t for t in open_tickets if t["account_id"] == aid]
            surge_alerts.append({
                "account_id": aid,
                "account_name": account_tickets[0].get("account_name"),
                "open_ticket_count": count,
                "tickets": [t["ticket_id"] for t in account_tickets],
                "severity": "HIGH" if count >= 3 else "MEDIUM",
            })
    surge_alerts.sort(key=lambda x: -x["open_ticket_count"])

    # 3. Issue pattern clusters
    clusters = detect_issue_clusters(open_tickets)

    # 4. Carrier fault orders without resolution
    unresolved_carrier_faults = []
    for order in all_orders:
        if order.get("carrier_fault") and order["status"] == "BOOKED":
            window_end = order.get("pickup_window_end")
            if window_end:
                try:
                    end_dt = datetime.fromisoformat(str(window_end))
                    delay_hrs = (DATASET_SNAPSHOT - end_dt).total_seconds() / 3600
                    if delay_hrs > 0:
                        unresolved_carrier_faults.append({
                            "order_id": order["order_id"],
                            "account_id": order["account_id"],
                            "account_name": order.get("account_name"),
                            "carrier": order["carrier"],
                            "delay_hours": round(delay_hrs, 1),
                            "shipment_fee_inr": order.get("shipment_fee_inr"),
                            "severity": "HIGH" if delay_hrs > 4 else "MEDIUM",
                        })
                except Exception:
                    pass
    unresolved_carrier_faults.sort(key=lambda x: -x["delay_hours"])

    # Summary
    critical_count = sum(1 for s in sla_alerts if s["breached"])
    return {
        "snapshot_time": DATASET_SNAPSHOT.isoformat(),
        "summary": {
            "open_tickets": len(open_tickets),
            "sla_breaches": critical_count,
            "sla_approaching": len(sla_alerts) - critical_count,
            "account_surges": len(surge_alerts),
            "pattern_clusters": len(clusters),
            "unresolved_carrier_faults": len(unresolved_carrier_faults),
        },
        "sla_alerts": sla_alerts,
        "surge_alerts": surge_alerts,
        "issue_clusters": clusters,
        "carrier_fault_orders": unresolved_carrier_faults,
    }
