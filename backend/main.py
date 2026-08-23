"""
FastAPI Main Application
Exposes chat, auth, proactive insights, and data endpoints.
"""

import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from auth.mock_auth import authenticate, login as mock_login, AuthUser
from agent.orchestrator import run_agent
from proactive.detector import get_proactive_insights

app = FastAPI(title="ParcelPilot AI Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(req: LoginRequest):
    result = mock_login(req.email, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


def get_current_user(authorization: str = Header(...)) -> AuthUser:
    token = authorization.replace("Bearer ", "").strip()
    user = authenticate(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@app.get("/auth/me")
def me(user: AuthUser = Depends(get_current_user)):
    return user


# ── Chat ──────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, user: AuthUser = Depends(get_current_user)):
    """
    SSE streaming chat endpoint.
    Yields JSON-encoded events for: tool_start, tool_result, text, pending_action, done
    """
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_generator():
        async for event in run_agent(messages, user):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/chat/confirm-action")
async def confirm_action(
    action: dict,
    user: AuthUser = Depends(get_current_user)
):
    """
    Execute a confirmed state-changing action.
    Called after user clicks 'Confirm' in the UI.
    """
    from agent.tools.action_executor import (
        execute_escalation, execute_ticket_update, execute_followup_task
    )

    action_type = action.get("action_type")
    details = action.get("details", {})

    if action_type == "escalation":
        result = execute_escalation(
            ticket_id=details["ticket_id"],
            account_id=details["account_id"],
            reason=details["reason"],
            priority=details["priority"],
            created_by=user.user_id,
        )
    elif action_type == "ticket_update":
        result = execute_ticket_update(
            ticket_id=details["ticket_id"],
            new_status=details["new_status"],
            note=details["note"],
            updated_by=user.user_id,
        )
    elif action_type == "followup_task":
        result = execute_followup_task(
            ticket_id=details["ticket_id"],
            account_id=details["account_id"],
            task=details["task"],
            assigned_to=details["assigned_to"],
            due_at=details["due_at"],
            created_by=user.user_id,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")

    return result


# ── Proactive Insights ────────────────────────────────────────────────────────

@app.get("/insights")
def get_insights(user: AuthUser = Depends(get_current_user)):
    """Staff only: proactive issue detection insights."""
    if user.role != "staff":
        raise HTTPException(status_code=403, detail="Access denied: Staff only")
    return get_proactive_insights()


# ── Data (read-only, for UI display) ─────────────────────────────────────────

@app.get("/data/accounts")
def list_accounts(user: AuthUser = Depends(get_current_user)):
    """Staff: list all accounts. Customer: their own account only."""
    from agent.tools.data_query import get_account, get_all_orders
    if user.role == "staff":
        import sqlite3
        import os
        db_path = os.getenv("DB_PATH", "./db/parcelPilot.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM accounts").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    else:
        result = get_account(user.account_id, requesting_account_id=user.account_id)
        return [result.get("data")] if "data" in result else []


@app.get("/data/orders")
def list_orders(user: AuthUser = Depends(get_current_user)):
    from agent.tools.data_query import get_orders_for_account, get_all_orders
    if user.role == "staff":
        result = get_all_orders()
        return result.get("data", [])
    else:
        result = get_orders_for_account(user.account_id, requesting_account_id=user.account_id)
        return result.get("data", [])


@app.get("/data/tickets")
def list_tickets(user: AuthUser = Depends(get_current_user)):
    from agent.tools.data_query import get_tickets_for_account, get_all_open_tickets
    if user.role == "staff":
        result = get_all_open_tickets()
        return result.get("data", [])
    else:
        result = get_tickets_for_account(user.account_id, requesting_account_id=user.account_id)
        return result.get("data", [])


@app.get("/health")
def health():
    return {"status": "ok", "service": "ParcelPilot AI Agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
