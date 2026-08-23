"""
Orchestrator Agent
Uses Google GenAI SDK (native) with function calling to coordinate multi-step
reasoning across doc_search, data_query, and action_executor tools.
All google.genai imports are deferred inside run_agent so the module loads instantly.
"""

import json
import os
from typing import AsyncGenerator
from dotenv import load_dotenv

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

MODEL = "gemini-3.5-flash-lite"
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

# Cached lazy-initialized SDK objects
_genai_client = None
_tool_declarations = None


def _get_sdk():
    """Lazy-import google.genai so the module loads instantly at server startup."""
    global _genai_client, _tool_declarations
    if _genai_client is not None:
        return _genai_client, _tool_declarations

    import google.genai as genai
    from google.genai import types

    _genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

    _tool_declarations = types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="doc_search",
            description="Search policy documents, customer agreements, SOPs, and product guides. Use for ANY policy/cancellation/SLA/credit/procedure questions.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="Natural language question to search for")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="get_account",
            description="Look up account details: plan tier, CSM, contract status.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"account_id": types.Schema(type="STRING")},
                required=["account_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_order",
            description="Look up order: status, carrier, pickup window, fees, fault attribution.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"order_id": types.Schema(type="STRING")},
                required=["order_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_orders_for_account",
            description="List all orders for a specific account.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"account_id": types.Schema(type="STRING")},
                required=["account_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_ticket",
            description="Look up a support ticket by ID.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"ticket_id": types.Schema(type="STRING")},
                required=["ticket_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_tickets_for_account",
            description="List all support tickets for a specific account.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"account_id": types.Schema(type="STRING")},
                required=["account_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_all_open_tickets",
            description="STAFF ONLY: Get all open tickets across all accounts.",
        ),
        types.FunctionDeclaration(
            name="get_all_orders",
            description="STAFF ONLY: Get all orders across all accounts.",
        ),
        types.FunctionDeclaration(
            name="prepare_escalation",
            description="Prepare a ticket escalation. Returns pending action requiring user confirmation before executing.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "account_id": types.Schema(type="STRING"),
                    "reason": types.Schema(type="STRING"),
                    "priority": types.Schema(type="STRING", enum=["P1", "P2", "P3"]),
                },
                required=["ticket_id", "account_id", "reason", "priority"]
            )
        ),
        types.FunctionDeclaration(
            name="execute_escalation",
            description="Execute a confirmed escalation. ONLY call after explicit user confirmation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "account_id": types.Schema(type="STRING"),
                    "reason": types.Schema(type="STRING"),
                    "priority": types.Schema(type="STRING"),
                },
                required=["ticket_id", "account_id", "reason", "priority"]
            )
        ),
        types.FunctionDeclaration(
            name="prepare_ticket_update",
            description="Prepare a ticket status update. Returns pending action requiring confirmation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "new_status": types.Schema(type="STRING"),
                    "note": types.Schema(type="STRING"),
                },
                required=["ticket_id", "new_status", "note"]
            )
        ),
        types.FunctionDeclaration(
            name="execute_ticket_update",
            description="Execute a confirmed ticket update. ONLY after user confirmation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "new_status": types.Schema(type="STRING"),
                    "note": types.Schema(type="STRING"),
                },
                required=["ticket_id", "new_status", "note"]
            )
        ),
        types.FunctionDeclaration(
            name="prepare_followup_task",
            description="Prepare a follow-up task for a ticket. Returns pending action requiring confirmation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "account_id": types.Schema(type="STRING"),
                    "task": types.Schema(type="STRING"),
                    "assigned_to": types.Schema(type="STRING"),
                    "due_at": types.Schema(type="STRING"),
                },
                required=["ticket_id", "account_id", "task", "assigned_to", "due_at"]
            )
        ),
        types.FunctionDeclaration(
            name="execute_followup_task",
            description="Execute a confirmed follow-up task. ONLY after user confirmation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "ticket_id": types.Schema(type="STRING"),
                    "account_id": types.Schema(type="STRING"),
                    "task": types.Schema(type="STRING"),
                    "assigned_to": types.Schema(type="STRING"),
                    "due_at": types.Schema(type="STRING"),
                },
                required=["ticket_id", "account_id", "task", "assigned_to", "due_at"]
            )
        ),
    ])

    return _genai_client, _tool_declarations


def _call_tool(name: str, args: dict, user: AuthUser) -> dict:
    """Dispatch tool call and enforce access control."""
    account_id = user.account_id
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
    Uses the native Google GenAI SDK (deferred import) for thought-signature safety.
    Yields dicts: 'tool_start', 'tool_result', 'text', 'pending_action', 'done'
    """
    tool_calls_made = []

    try:
        import google.genai as genai
        from google.genai import types

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

        # Get (or lazily initialize) the SDK client and tool declarations
        client, tool_declarations = _get_sdk()

        # Build conversation history in native GenAI format
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        last_message = messages[-1]["content"] if messages else ""

        chat = client.chats.create(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[tool_declarations],
                temperature=0.1,
            ),
            history=history,
        )

        current_message = last_message
        for _ in range(10):
            try:
                response = chat.send_message(current_message)
            except Exception as e:
                print(f"[orchestrator] API error: {e}")
                yield {"type": "text", "content": "I'm currently experiencing an API error. Please try again in a few moments."}
                return

            has_tool_calls = False
            text_parts = []

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_tool_calls = True
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args) if part.function_call.args else {}

                    yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

                    result = _call_tool(tool_name, tool_args, user)
                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": result})

                    if result.get("status") == "pending_confirmation":
                        yield {"type": "tool_result", "tool": tool_name, "result": result}
                        yield {"type": "pending_action", "action": result}
                        return

                    yield {"type": "tool_result", "tool": tool_name, "result": result}

                elif part.text:
                    text_parts.append(part.text)

            if has_tool_calls:
                # Build tool result parts for the next turn
                tool_results = []
                recent_calls = [e for e in tool_calls_made
                                if e not in tool_calls_made[:-len([p for p in response.candidates[0].content.parts if p.function_call])]]
                for p in response.candidates[0].content.parts:
                    if p.function_call:
                        # Find matching result
                        matching = next(
                            (e for e in reversed(tool_calls_made) if e["tool"] == p.function_call.name),
                            None
                        )
                        if matching:
                            tool_results.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=p.function_call.name,
                                        response={"result": json.dumps(matching["result"], default=str)}
                                    )
                                )
                            )
                current_message = tool_results
            else:
                final_text = "".join(text_parts)
                if not final_text:
                    yield {"type": "text", "content": "I'm having trouble generating a response. Please try again."}
                else:
                    yield {"type": "text", "content": final_text}
                return

        yield {"type": "text", "content": "I've gathered all the information. Let me know if you have any questions."}

    except Exception as e:
        print(f"[orchestrator] Fatal error in run_agent: {e}")
        yield {"type": "text", "content": "⚠️ An unexpected error occurred while processing your request."}
    finally:
        yield {"type": "done", "tool_calls": tool_calls_made}
