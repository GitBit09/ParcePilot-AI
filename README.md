# ParcelPilot AI Agent

> AI-powered support agent system for ParcelPilot logistics SaaS.
> Built for the CalQuity AI Engineer Assessment.

## Live Demo

- **Frontend**: [Deployed on Vercel](https://parcelPilot-ai.vercel.app) *(link after deployment)*
- **Backend API**: [Deployed on Render](https://parcelPilot-api.onrender.com) *(link after deployment)*

---

## Architecture

```
Frontend (Next.js 14) ──SSE streaming──▶ Backend (FastAPI + Python 3.11)
                                                    │
                          ┌─────────────────────────┤
                          │                         │
                    FAISS RAG              SQLite (from XLSX)
                    (6 PDFs)           (accounts/orders/tickets)
                          │                         │
                    Gemini 2.0 Flash ◀──────────────┘
                    (Tool Calling)
```

### Agent Tools
| Tool | Purpose |
|------|---------|
| `doc_search` | RAG over PDFs with source priority |
| `data_query` | SQL over structured data, access-scoped |
| `action_executor` | Escalation / ticket update / follow-up task |

### Source Priority
1. Signed customer agreements (highest — override everything)
2. Current policies/SOPs
3. Product operations guide
4. Historical tickets (context only — **may be wrong**)
5. Deprecated docs (**never used**)

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com)

### 1. Clone & Setup Backend

```bash
cd backend

# Create venv (recommended: use uv)
pip install uv
uv venv .venv --python 3.11
.venv\Scripts\activate    # Windows
# or: source .venv/bin/activate  # Mac/Linux

# Install packages
uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

# Build database + RAG index (one-time setup, ~2-3 min)
python -m db.setup
python -m rag.indexer

# Start backend
python main.py
# Runs at http://localhost:8000
```

### 2. Setup Frontend

```bash
cd frontend
npm install
npm run dev
# Runs at http://localhost:3000
```

### 3. Login

Use any demo account from the login page quick-select, or:

| Email | Password | Role |
|-------|----------|------|
| `northstar@parcelPilot.com` | `northstar123` | Customer (Northstar) |
| `lumenworks@parcelPilot.com` | `lumenworks123` | Customer (LumenWorks) |
| `beacon@parcelPilot.com` | `beacon123` | Customer (Beacon Retail) |
| `axislabs@parcelPilot.com` | `axislabs123` | Customer (Axis Labs) |
| `rohit@parcelPilot.com` | `staff123` | Staff (Support Agent) |
| `maya@parcelPilot.com` | `staff123` | Staff (Support Agent) |
| `priya@parcelPilot.com` | `staff123` | Staff (CSM) |

---

## Example Queries to Try

### Customer (Northstar)
- *"Can I cancel ORD-1001 without a cancellation fee?"*
- *"What is my P1 SLA response time?"*
- *"Show me all my open tickets"*

### Staff
- *"Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."*
- *"A pickup is 3 hours late due to carrier fault for LumenWorks — do they get a credit?"*
- *"Escalate TKT-501 to P1 priority"*
- *"What is the correct answer for TKT-450's historical resolution?"*

---

## Key Design Decisions

### Source Reliability
- Deprecated v2 policy never returned in search results (excluded at retrieval layer)
- Customer agreements checked first — if a signed agreement exists, it overrides default policy
- Historical ticket resolutions flagged with known-incorrect warnings (TKT-450, TKT-451)
- Every answer cites sources with priority ranking

### Access Control
- Enforced at the **data/tool layer** — not relying on prompt instructions
- Customer tokens return data only for their own account_id (SQL WHERE clause)
- Staff tools (`get_all_open_tickets`, `get_all_orders`) blocked for customer role

### Confirmation Gate
- All state-changing actions (escalate, update, create task) use a prepare→confirm→execute pattern
- The `prepare_*` functions return `pending_confirmation` status
- Frontend shows a confirmation dialog; only calls `execute_*` after user clicks Confirm

### Proactive Detection
- SLA targets encoded per customer (Northstar: 15min P1, vs standard 30min)
- Runs without user prompting — displayed in the Ops Dashboard Issue Radar
- Detects: SLA breaches, multi-ticket surges, issue pattern clusters, unresolved carrier faults

---

## AI Tool Usage

Built with **Antigravity IDE** (Google Deepmind AI coding assistant) for code generation and architecture, with **Gemini 2.0 Flash** as the agent LLM.

---

## Submission

- [Task Submission Form](https://forms.gle/hLGBrDrNRmK7UAbv6)
