# Product Note

## Which Additional Problem I Addressed

I addressed **both** bonus problems.

### Problem 1: Proactive Issue Detection

Built an **Issue Radar** dashboard (`/ops`) for internal staff that surfaces issues automatically — without anyone asking a question. It runs four detectors against the live database:

1. **SLA breach detection** — compares each open ticket's age against per-account SLA targets (e.g., Northstar has a 15-minute P1 SLA, not the standard 30 minutes). Flags BREACHED and APPROACHING tickets.
2. **Account surge detection** — identifies accounts with 2+ simultaneous open tickets, which often signals a product-level issue rather than isolated support requests.
3. **Issue pattern clustering** — groups tickets by keyword patterns (bulk upload failures, carrier pickup delays, API key exposure, etc.) and flags when the same pattern appears across multiple accounts.
4. **Unresolved carrier fault orders** — finds orders where `carrier_fault = true` but the status is still BOOKED past the pickup window, indicating a customer may be entitled to a service credit that hasn't been processed.

### Problem 2: Trust and Reliability

The source reliability architecture is deliberate throughout:
- **Deprecated docs excluded at the retrieval layer** — not just instructed away in the prompt. The FAISS search filters `status == "DEPRECATED"` before returning results.
- **Customer agreements take priority over general policy** — the agent is instructed to check agreements first and the retriever preferentially surfaces account-specific documents for the requesting account.
- **Known-incorrect resolutions are flagged** — TKT-450 (wrongly applied cancellation fee to Northstar) and TKT-451 (wrongly blamed plan limits for a known bug) are documented in `KNOWN_WRONG_RESOLUTIONS`. When the agent references these tickets, it can proactively flag the conflict.
- **Uncertainty handled explicitly** — if data conflicts or the agent can't answer confidently, it says so and recommends human review rather than guessing.

---

## What Else I Would Build for ParcelPilot

**Conversation memory across sessions** — currently each chat session starts fresh. Storing conversation history per user would let the agent remember context ("last time we talked about your ORD-1001 cancellation...").

**Feedback loop on AI responses** — a thumbs up/down on each message. The thumbs-down cases (especially ones that lead to human escalation) would be the highest-signal dataset for improving RAG and the system prompt.

**Agent-initiated escalations** — if the agent detects a P1 pattern (e.g., multiple accounts reporting the same outage), it should be able to proactively draft an escalation and surface it to staff without a customer having to ask.

**Real authentication** — replace mock tokens with Google/GitHub OAuth. Zero friction for the customer, and gives you real user identity for audit trails on actions.

**Analytics dashboard** — track containment rate (tickets resolved without human), average tool calls per query, most common question categories, and escalation rate by account tier.

---

## What I Intentionally Left Out

**Real carrier API integrations** — order status, pickup tracking, and carrier fault attribution are all from the static dataset. In production these would be live API calls.

**Email/Slack notifications** — the proactive radar surfaces issues in the UI but doesn't push alerts. A cron job sending Slack messages for P1 SLA breaches would be the natural next step.

**Fine-tuning or RAG feedback** — the current retrieval is semantic search only. A production system would track which retrieved chunks led to good vs. bad answers and use that to improve the index.

**Multi-language support** — all queries are assumed to be in English.

---

## The One Metric I Would Use

**Containment rate**: the percentage of support sessions that are fully resolved by the AI without a human agent needing to intervene.

This is the metric that directly answers whether the product is useful. A high containment rate means customers are getting accurate answers faster, and the support team's time is being freed up for the cases that genuinely need human judgment. It also catches trust failures — if containment rate drops after a policy change, the RAG index is probably stale.
