"""
Tool 3: Action Executor
Handles state-changing actions: escalations, ticket updates, follow-up tasks.
ALL actions require explicit user confirmation before execution.
"""

import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./db/parcelPilot.db")

DATASET_SNAPSHOT_STR = "2026-08-16T11:00:00"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def prepare_escalation(
    ticket_id: str,
    account_id: str,
    reason: str,
    priority: str,
    created_by: str,
) -> dict:
    """
    Prepare an escalation (NOT yet executed).
    Returns a pending_action dict that must be confirmed by the user.
    """
    return {
        "tool": "action_executor",
        "action_type": "escalation",
        "status": "pending_confirmation",
        "summary": f"Escalate ticket {ticket_id} to {priority} priority",
        "details": {
            "ticket_id": ticket_id,
            "account_id": account_id,
            "reason": reason,
            "priority": priority,
            "created_by": created_by,
        },
        "confirmation_message": (
            f"⚡ Ready to escalate **{ticket_id}** as **{priority}** priority.\n\n"
            f"**Reason:** {reason}\n\n"
            f"Do you want to proceed?"
        ),
    }


def execute_escalation(
    ticket_id: str,
    account_id: str,
    reason: str,
    priority: str,
    created_by: str,
) -> dict:
    """Execute a confirmed escalation."""
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO escalations (ticket_id, account_id, reason, priority, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, account_id, reason, priority, created_by, now)
        )
        conn.execute(
            "UPDATE tickets SET status = 'escalated' WHERE ticket_id = ?",
            (ticket_id,)
        )
        conn.commit()

    return {
        "tool": "action_executor",
        "action_type": "escalation",
        "status": "executed",
        "message": f"✅ Ticket {ticket_id} has been escalated to {priority} priority.",
        "ticket_id": ticket_id,
        "priority": priority,
        "created_at": now,
    }


def prepare_ticket_update(
    ticket_id: str,
    new_status: str,
    note: str,
    updated_by: str,
) -> dict:
    """Prepare a ticket status update (requires confirmation)."""
    return {
        "tool": "action_executor",
        "action_type": "ticket_update",
        "status": "pending_confirmation",
        "summary": f"Update ticket {ticket_id} status to '{new_status}'",
        "details": {
            "ticket_id": ticket_id,
            "new_status": new_status,
            "note": note,
            "updated_by": updated_by,
        },
        "confirmation_message": (
            f"📝 Ready to update **{ticket_id}** status to **{new_status}**.\n\n"
            f"**Note:** {note}\n\n"
            f"Do you want to proceed?"
        ),
    }


def execute_ticket_update(ticket_id: str, new_status: str, note: str, updated_by: str) -> dict:
    """Execute a confirmed ticket update."""
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "UPDATE tickets SET status = ? WHERE ticket_id = ?",
            (new_status, ticket_id)
        )
        conn.commit()

    return {
        "tool": "action_executor",
        "action_type": "ticket_update",
        "status": "executed",
        "message": f"✅ Ticket {ticket_id} updated to status '{new_status}'.",
        "ticket_id": ticket_id,
        "new_status": new_status,
        "updated_by": updated_by,
        "updated_at": now,
    }


def prepare_followup_task(
    ticket_id: str,
    account_id: str,
    task: str,
    assigned_to: str,
    due_at: str,
    created_by: str,
) -> dict:
    """Prepare a follow-up task (requires confirmation)."""
    return {
        "tool": "action_executor",
        "action_type": "followup_task",
        "status": "pending_confirmation",
        "summary": f"Create follow-up task for {ticket_id}",
        "details": {
            "ticket_id": ticket_id,
            "account_id": account_id,
            "task": task,
            "assigned_to": assigned_to,
            "due_at": due_at,
            "created_by": created_by,
        },
        "confirmation_message": (
            f"📌 Ready to create follow-up task for **{ticket_id}**.\n\n"
            f"**Task:** {task}\n"
            f"**Assigned to:** {assigned_to}\n"
            f"**Due:** {due_at}\n\n"
            f"Do you want to proceed?"
        ),
    }


def execute_followup_task(
    ticket_id: str, account_id: str, task: str,
    assigned_to: str, due_at: str, created_by: str
) -> dict:
    """Execute a confirmed follow-up task creation."""
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        cursor = conn.execute(
            "INSERT INTO followup_tasks (ticket_id, account_id, task, assigned_to, created_by, created_at, due_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, account_id, task, assigned_to, created_by, now, due_at)
        )
        conn.commit()
        task_id = cursor.lastrowid

    return {
        "tool": "action_executor",
        "action_type": "followup_task",
        "status": "executed",
        "message": f"✅ Follow-up task #{task_id} created for ticket {ticket_id}.",
        "task_id": task_id,
        "assigned_to": assigned_to,
        "due_at": due_at,
    }
