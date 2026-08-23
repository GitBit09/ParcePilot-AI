"""
Tool 2: Structured Data Query
Queries the SQLite database (accounts, orders, tickets).
Access is enforced at this layer — customers can ONLY see their own account data.
"""

import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./db/parcelPilot.db")

# Dataset reference time
DATASET_SNAPSHOT = datetime(2026, 8, 16, 11, 0, 0)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_account(account_id: str, requesting_account_id: str | None = None) -> dict:
    """Look up account info. Enforces access control."""
    if requesting_account_id and requesting_account_id != account_id:
        return {"error": "Access denied: You can only view your own account.", "tool": "data_query"}

    with _conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
        if not row:
            return {"error": f"Account {account_id} not found.", "tool": "data_query"}
        return {"tool": "data_query", "type": "account", "data": dict(row)}


def get_order(order_id: str, requesting_account_id: str | None = None) -> dict:
    """Look up order. Enforces access control."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": f"Order {order_id} not found.", "tool": "data_query"}

        order = dict(row)

        # Enforce access control
        if requesting_account_id and order["account_id"] != requesting_account_id:
            return {"error": "Access denied: This order does not belong to your account.", "tool": "data_query"}

        # Calculate pickup delay if relevant
        extra = {}
        if order.get("pickup_window_end") and not order.get("pickup_actual_at"):
            try:
                window_end = datetime.fromisoformat(order["pickup_window_end"])
                delay_minutes = (DATASET_SNAPSHOT - window_end).total_seconds() / 60
                if delay_minutes > 0:
                    extra["pickup_delay_minutes"] = round(delay_minutes)
                    extra["pickup_delay_hours"] = round(delay_minutes / 60, 2)
            except Exception:
                pass

        return {"tool": "data_query", "type": "order", "data": order, **extra}


def get_orders_for_account(account_id: str, requesting_account_id: str | None = None) -> dict:
    """List all orders for an account."""
    if requesting_account_id and requesting_account_id != account_id:
        return {"error": "Access denied.", "tool": "data_query"}

    with _conn() as conn:
        rows = conn.execute("SELECT * FROM orders WHERE account_id = ?", (account_id,)).fetchall()
        return {"tool": "data_query", "type": "orders_list", "account_id": account_id,
                "data": [dict(r) for r in rows], "count": len(rows)}


def get_ticket(ticket_id: str, requesting_account_id: str | None = None) -> dict:
    """Look up a support ticket."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if not row:
            return {"error": f"Ticket {ticket_id} not found.", "tool": "data_query"}

        ticket = dict(row)

        if requesting_account_id and ticket["account_id"] != requesting_account_id:
            return {"error": "Access denied: This ticket does not belong to your account.", "tool": "data_query"}

        # Flag if historical_resolution might be wrong
        from agent.source_registry import KNOWN_WRONG_RESOLUTIONS
        warnings = []
        if ticket_id in KNOWN_WRONG_RESOLUTIONS:
            info = KNOWN_WRONG_RESOLUTIONS[ticket_id]
            warnings.append(f"⚠️ KNOWN INCORRECT RESOLUTION: {info['wrong_claim']}. "
                            f"Correction: {info['correction']}")

        return {"tool": "data_query", "type": "ticket", "data": ticket,
                "historical_resolution_warnings": warnings}


def get_tickets_for_account(account_id: str, requesting_account_id: str | None = None) -> dict:
    """List all tickets for an account."""
    if requesting_account_id and requesting_account_id != account_id:
        return {"error": "Access denied.", "tool": "data_query"}

    with _conn() as conn:
        rows = conn.execute("SELECT * FROM tickets WHERE account_id = ?", (account_id,)).fetchall()
        return {"tool": "data_query", "type": "tickets_list", "account_id": account_id,
                "data": [dict(r) for r in rows], "count": len(rows)}


def get_all_open_tickets() -> dict:
    """Staff only: get all open tickets across all accounts."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT t.*, a.account_name, a.plan FROM tickets t "
            "JOIN accounts a ON t.account_id = a.account_id "
            "WHERE t.status = 'open' ORDER BY t.created_at"
        ).fetchall()
        return {"tool": "data_query", "type": "all_open_tickets", "data": [dict(r) for r in rows]}


def get_all_orders() -> dict:
    """Staff only: get all orders."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT o.*, a.account_name FROM orders o "
            "JOIN accounts a ON o.account_id = a.account_id"
        ).fetchall()
        return {"tool": "data_query", "type": "all_orders", "data": [dict(r) for r in rows]}
