"""
Orchestrator Agent
Uses Groq (llama-3.3-70b-versatile) with function calling to coordinate multi-step
reasoning across doc_search, data_query, and action_executor tools.
"""

import json
import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from openai import OpenAI

from agent.tools.doc_search import doc_search
from agent.tools.data_query import (
    get_account, get_order, get_orders_for_account,
    get_ticket, get_tickets_for_account, get_all_open_tickets, get_all_orders
)
from agent.tools.action_executor import (
    prepare_escalation, execute_escalation,
    prepare_ticket_update, execute_ticket_update,
    prepare_followup_task, execute_followup_task,
)
from auth.mock_auth import AuthUser

load_dotenv()

def _make_client(key: str) -> OpenAI:
    return OpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

_primary_key   = os.getenv("GEMINI_API_KEY", "")
_clients       = [_make_client(_primary_key)] if _primary_key else []
_client_idx    = 0

def _get_client() -> OpenAI:
    return _clients[_client_idx % len(_clients)]

def _rotate_client():
    global _client_idx
    _client_idx += 1
    print(f"[orchestrator] Rotated to backup Gemini key (index {_client_idx % max(1, len(_clients))})")

MODEL = "gemini-3.5-flash"
DATASET_SNAPSHOT = "2026-08-16 11:00 IST"

SYSTEM_PROMPT = """You are ParcelPilot's AI support assistant. ParcelPilot is a logistics SaaS platform.

REFERENCE TIME: All "current" data is as of the dataset snapshot: {snapshot}. Treat this as "now".

YOUR ROLE:
- {role_context}

SOURCE RELIABILITY (always follow this hierarchy):
1. CUSTOMER AGREEMENTS (files 05_, 06_) — highest authority; override all default policies
2. CURRENT POLICIES/SOPs (files 01_, 03_, 04_) — default rules when no agreement overrides
3. HISTORICAL TICKETS — context only; they may contain INCORRECT past guidance. Flag conflicts.
4. DEPRECATED DOCS (file 02_) — NEVER use to answer questions

KEY RULES:
- Always use the correct source hierarchy. If a customer has a signed agreement, it overrides general policy.
- If historical ticket resolution contradicts current policy, explicitly flag the discrepancy.
- For state-changing actions (escalations, ticket updates), always use the prepare_ functions first. Never execute an action until the user has confirmed.
- If data conflicts or is unclear, say so and recommend human review rather than guessing.
- Always cite your sources in your answer.
- If a query requires multiple steps, work through them one at a time.
- Customer users can only access their own account data. Never reveal other customers' data.

AVAILABLE TOOLS: doc_search, get_account, get_order, get_orders_for_account, get_ticket, get_tickets_for_account, {staff_tools}prepare_escalation, execute_escalation, prepare_ticket_update, execute_ticket_update, prepare_followup_task, execute_followup_task
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "doc_search",
            "description": "Search policy documents, customer agreements, SOPs, and product guides. Use for ANY policy/cancellation/SLA/credit/procedure questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language question to search for"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account",
            "description": "Look up account details: plan tier, CSM, contract status.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up order: status, carrier, pickup window, fees, fault attribution.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_for_account",
            "description": "List all orders for a specific account.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Look up a support ticket by ID.",
            "parameters": {
                "type": "object",
                "properties": {"ticket_id": {"type": "string"}},
                "required": ["ticket_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tickets_for_account",
            "description": "List all support tickets for a specific account.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_open_tickets",
            "description": "STAFF ONLY: Get all open tickets across all accounts.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_orders",
            "description": "STAFF ONLY: Get all orders across all accounts.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_escalation",
            "description": "Prepare a ticket escalation. Returns pending action requiring user confirmation before executing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "account_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3"]}
                },
                "required": ["ticket_id", "account_id", "reason", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_escalation",
            "description": "Execute a confirmed escalation. ONLY call after explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "account_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "string"}
                },
                "required": ["ticket_id", "account_id", "reason", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_ticket_update",
            "description": "Prepare a ticket status update. Returns pending action requiring confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "new_status": {"type": "string"},
                    "note": {"type": "string"}
                },
                "required": ["ticket_id", "new_status", "note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_ticket_update",
            "description": "Execute a confirmed ticket update. ONLY after user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "new_status": {"type": "string"},
                    "note": {"type": "string"}
                },
                "required": ["ticket_id", "new_status", "note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_followup_task",
            "description": "Prepare a follow-up task for a ticket. Returns pending action requiring confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "account_id": {"type": "string"},
                    "task": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "due_at": {"type": "string"}
                },
                "required": ["ticket_id", "account_id", "task", "assigned_to", "due_at"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_followup_task",
            "description": "Execute a confirmed follow-up task. ONLY after user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "account_id": {"type": "string"},
                    "task": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "due_at": {"type": "string"}
                },
                "required": ["ticket_id", "account_id", "task", "assigned_to", "due_at"]
            }
        }
    },
]


def _call_tool(name: str, args: dict, user: AuthUser) -> dict:
    """Dispatch tool call and enforce access control."""
    account_id = user.account_id  # None for staff
    is_staff = user.role == "staff"

    if name in ("get_all_open_tickets", "get_all_orders") and not is_staff:
        return {"error": "Access denied: This tool is only available to ParcelPilot staff."}

    if name == "doc_search":
        return doc_search(args["query"], account_id=account_id, top_k=args.get("top_k", 6))
    elif name == "get_account":
        return get_account(args["account_id"], requesting_account_id=account_id)
    elif name == "get_order":
        return get_order(args["order_id"], requesting_account_id=account_id)
    elif name == "get_orders_for_account":
        return get_orders_for_account(args["account_id"], requesting_account_id=account_id)
    elif name == "get_ticket":
        return get_ticket(args["ticket_id"], requesting_account_id=account_id)
    elif name == "get_tickets_for_account":
        return get_tickets_for_account(args["account_id"], requesting_account_id=account_id)
    elif name == "get_all_open_tickets":
        return get_all_open_tickets()
    elif name == "get_all_orders":
        return get_all_orders()
    elif name == "prepare_escalation":
        return prepare_escalation(**args, created_by=user.user_id)
    elif name == "execute_escalation":
        return execute_escalation(**args, created_by=user.user_id)
    elif name == "prepare_ticket_update":
        return prepare_ticket_update(**args, updated_by=user.user_id)
    elif name == "execute_ticket_update":
        return execute_ticket_update(**args, updated_by=user.user_id)
    elif name == "prepare_followup_task":
        return prepare_followup_task(**args, created_by=user.user_id)
    elif name == "execute_followup_task":
        return execute_followup_task(**args, created_by=user.user_id)
    else:
        return {"error": f"Unknown tool: {name}"}


async def run_agent(
    messages: list[dict],
    user: AuthUser,
) -> AsyncGenerator[dict, None]:
    """
    Run the orchestrator agent and yield SSE-compatible events.
    Yields dicts: 'tool_start', 'tool_result', 'text', 'pending_action', 'done'
    """
    is_staff = user.role == "staff"

    role_context = (
        f"You are helping {user.display_name} ({user.account_name} — customer). "
        f"They can only access data for their own account ({user.account_id})."
        if not is_staff else
        f"You are helping {user.display_name}, a ParcelPilot support staff member. "
        f"You have full access to all accounts, orders, and tickets."
    )

    staff_tools = "get_all_open_tickets, get_all_orders, " if is_staff else ""

    system_prompt = SYSTEM_PROMPT.format(
        snapshot=DATASET_SNAPSHOT,
        role_context=role_context,
        staff_tools=staff_tools,
    )

    # Build Groq message history (OpenAI-compatible format)
    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        groq_messages.append({
            "role": "user" if msg["role"] == "user" else "assistant",
            "content": msg["content"]
        })

    tool_calls_made = []

    try:
        # We will loop for a maximum of 10 back-and-forth turns for tool calls
        for _ in range(10):
            for attempt in range(max(1, len(_clients))):
                try:
                    response = _get_client().chat.completions.create(
                        model=MODEL,
                        messages=groq_messages,
                        tools=TOOL_DEFINITIONS,
                        tool_choice="auto",
                        max_tokens=4096,
                    )
                    break
                except Exception as e:
                    print(f"[orchestrator] API error: {e}")
                    _rotate_client()
            else:
                yield {"type": "text", "content": "I'm currently experiencing high traffic or an API error. Please try again in a few moments."}
                return

            msg = response.choices[0].message
            
            # Append assistant message to history
            groq_messages.append(msg)

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except Exception:
                        tool_args = {}

                    yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

                    result = _call_tool(tool_name, tool_args, user)
                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": result})

                    # Check for pending confirmation
                    if result.get("status") == "pending_confirmation":
                        yield {"type": "tool_result", "tool": tool_name, "result": result}
                        yield {"type": "pending_action", "action": result}
                        return

                    yield {"type": "tool_result", "tool": tool_name, "result": result}

                    # Feed result back into history (Gemini compatibility requires 'name')
                    groq_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": json.dumps(result, default=str)
                    })
            else:
                # Final text response
                text = msg.content or ""
                yield {"type": "text", "content": text}
                return

        yield {"type": "text", "content": "I've gathered all the information. Let me know if you have any questions."}
    except Exception as e:
        print(f"[orchestrator] Fatal error in run_agent: {e}")
        yield {"type": "text", "content": "\n\n⚠️ An unexpected error occurred while processing your request."}
    finally:
        yield {"type": "done", "tool_calls": tool_calls_made}
