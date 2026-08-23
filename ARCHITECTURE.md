# Architecture Note

## Agent Design

The system uses a **single orchestrator agent** powered by Gemini via the native `google-genai` SDK. The agent runs in an **agentic loop** (up to 10 turns) — it receives a user message, decides which tools to call, processes results, and calls more tools if needed until it can produce a final answer.

Two distinct agent contexts are supported from the same orchestrator:
- **Customer mode**: scoped to a single `account_id`, restricted tool set
- **Staff mode**: full cross-account access, additional staff-only tools

The agent streams responses over **Server-Sent Events (SSE)** so the UI can show tool activity in real time as each step completes.

## Tool Design

The agent has three distinct tool categories:

### 1. `doc_search` — Document Retrieval
Semantic search over 6 indexed PDF documents using a FAISS vector index. Queries are embedded with `gemini-embedding-2` at runtime and matched against pre-indexed chunks. Results are filtered by:
- **Deprecated status** — the v2 policy is never returned
- **Account scope** — customer-specific agreements are preferentially surfaced for the relevant account

### 2. `data_query` — Structured Data Lookup
SQL queries over a SQLite database built from the provided XLSX. Tools include:
`get_account`, `get_order`, `get_orders_for_account`, `get_ticket`, `get_tickets_for_account`, `get_all_open_tickets` (staff only), `get_all_orders` (staff only).

Every query accepts a `requesting_account_id` parameter. Customer queries include a `WHERE account_id = ?` guard — access control is enforced at the SQL layer, not just in the prompt.

### 3. `action_executor` — State-Changing Actions
Three action types: **escalation**, **ticket status update**, **follow-up task creation**. All follow a **prepare → confirm → execute** pattern:
- `prepare_*` returns a `pending_confirmation` dict — no database write
- The frontend renders a confirmation card and blocks until the user clicks Confirm
- Only then does the frontend call `/chat/confirm` to execute the action
- Actions are written to the SQLite database (escalations table, ticket updates, followup_tasks table)

## Document and Structured-Data Handling

**PDFs** are chunked at 400 characters with 80-character overlap and indexed with `gemini-embedding-2` (3072-dimensional embeddings) into a FAISS `IndexFlatL2`. The index is built during the Render build step using the `GEMINI_API_KEY` environment variable — no local model required.

**Structured data** (accounts, orders, tickets) is loaded from `ParcelPilot_Assessment_Data.xlsx` into SQLite via `openpyxl` during setup. The reference time is the dataset snapshot (`2026-08-16 11:00 IST`) as specified in the workbook's README sheet.

## Source Reliability and Conflict Handling

Source authority is defined in `source_registry.py` with explicit priority tiers:

| Priority | Source | Rule |
|---|---|---|
| 1 | Signed customer agreements (files 05_, 06_) | Override everything for that account |
| 2 | Current policies/SOPs (files 01_, 03_, 04_) | Default rules |
| 3 | Product operations guide (file 04_) | Product-specific facts |
| 9 | Historical ticket resolutions | Context only — **may be wrong** |
| 99 | Deprecated policy v2 (file 02_) | **Never returned** |

The system prompt explicitly instructs the model to follow this hierarchy. Two known-incorrect historical resolutions (TKT-450 and TKT-451) are documented in `KNOWN_WRONG_RESOLUTIONS` so the agent can proactively flag them.

When a customer agreement conflicts with general policy (e.g., Northstar's fee waiver vs. the standard INR 250 cancellation fee), `detect_conflict()` surfaces this explicitly and the agent cites both sources with a clear resolution.

## Major Technical Trade-offs

**Gemini embeddings over local model**: Replaced `sentence-transformers` (which pulled in 2GB of PyTorch/NVIDIA packages) with `gemini-embedding-2` via API. This reduced the Render build artifact from ~2GB to ~200MB, cutting build time from 10+ minutes to under 2 minutes and eliminating OOM risk on Render's 512MB free-tier instances. The embedding quality is also higher (3072-dim vs 384-dim).

**Synchronous agentic loop over streaming tool calls**: The agent loop runs synchronously within the FastAPI `StreamingResponse` generator — each tool result is yielded to the frontend before the next LLM call is made. This gives real-time visibility into which tools are being called without requiring WebSockets.

**SQLite over a managed database**: Keeps the stack simple and self-contained. The database is built from the XLSX during the Render build step and committed to the deployment artifact. Acceptable for an assessment; in production this would be replaced with Postgres.

**Mock authentication**: JWT-style bearer tokens stored in-memory. The access control logic (account scoping) is real and enforced in the data layer — only the token issuance is mocked.
