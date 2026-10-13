# Campus Customs — Agent Harness

The full reference for the Campus Customs multi-agent system: **tables → MCP tools → 5 agents → API routes → dashboard → safety**, plus the results of the full run.

**Contents:** [Tables](#tables) · [Working tables](#working-tables-added-by-the-mcp-server) · [Tickets](#the-three-open-tickets-and-how-they-link) · [Agent team](#agent-team-problem-5) · [MCP tools](#mcp-tools-all-18-final) · [Safety](#safety) · [API routes](#backend-routes-problem-7) · [Dashboard](#dashboard-problem-8) · [Full run results](#full-run-results-problem-9)

**Run it**
```bash
# 1. backend (from backend/)
uvicorn main:app --reload --port 8000
# 2. dashboard (from frontend/)
npm run dev
# fresh start: Reset shop button, or POST /api/reset
```

- **Original DB (never modified):** `data/campus_customs.db`
- **Working copy (all tools read/write here):** `data/campus_customs_new.db`
- **Shop "today":** `desk.date_today` = **2026-08-31**

---

## Tables

### `desk`
| field | type | notes |
|---|---|---|
| date_today | TEXT | the shop's "today" |
| notes | TEXT | free-form desk notes (empty) |

**Why it matters:** It is the single source of "today". Every overdue check and due-date calculation uses `date_today`, never the real clock.

### `tickets`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | ticket number |
| type | TEXT | `customer_order`, `rent_notice`, `price_override` |
| requester | TEXT | who opened it |
| subject | TEXT | short title |
| sku | TEXT | → `inventory.sku` / `pricing.sku` (if product-related) |
| size | TEXT | → `inventory.size` |
| qty | INTEGER | units requested |
| lease_id | INTEGER FK | → `leases.id` (if rent-related) |
| invoice_id | INTEGER FK | → `invoices.id` (if a bill is involved) |
| status | TEXT | `open` → resolved by agents |
| notes | TEXT | the request in plain words |
| created_at | TEXT | ISO timestamp |

**Why it matters:** This is the work board. Boss reads each ticket, and its `type` and link fields decide which agents get involved.

### `inventory`
| field | type | notes |
|---|---|---|
| sku | TEXT | product code (PK with size) |
| name | TEXT | product name |
| size | TEXT | S / M / L / XL / OS |
| qty | INTEGER | units on hand |
| location | TEXT | aisle |

**Why it matters:** Inventory uses it to check stock by SKU and size and to spot shortfalls.

### `pricing`
| field | type | notes |
|---|---|---|
| sku | TEXT PK | product code |
| unit_cost | REAL | what the shop pays |
| list_price | REAL | what the customer pays |

**Why it matters:** Accounting uses it to check margins (for example, whether a discount still makes money) and to cost restock orders.

### `vendors`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | vendor id |
| name | TEXT | vendor name |
| specialty | TEXT | what they supply |
| lead_days | INTEGER | days from order to delivery |

**Why it matters:** Inventory uses it to pick which vendor can restock an item. `lead_days` gives the expected arrival date (today + lead_days).

### `leases`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | lease id |
| space_name | TEXT | the shop space |
| landlord | TEXT | who gets paid |
| monthly_rent | REAL | rent amount |
| next_due | TEXT | next rent due date |
| notes | TEXT | |

**Why it matters:** Facilities uses it to confirm rent amounts and due dates. After rent is paid, `next_due` should move forward a month.

### `cash_accounts`
| field | type | notes |
|---|---|---|
| name | TEXT PK | account name |
| balance | REAL | current cash |
| date | TEXT | as-of date |

**Why it matters:** This is the only cash source. Every payment is deducted here, and the pay tool must refuse any payment that would make the balance negative. No money ever comes in.

### `payments`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | payment id |
| kind | TEXT | e.g. `invoice`, `rent`, `purchase_order` |
| ref_id | INTEGER | id of the invoice / lease / PO being paid |
| amount | REAL | amount paid |
| account | TEXT | → `cash_accounts.name` |
| paid_at | TEXT | date paid (shop date) |
| approved_by | TEXT | the human who approved; required |

**Why it matters:** This is the audit trail. A row appears only after a human approves a payment (it starts empty).

### `invoices`
| field | type | notes |
|---|---|---|
| id | INTEGER PK | invoice id |
| vendor_id | INTEGER FK | → `vendors.id` |
| amount | REAL | amount owed |
| due_date | TEXT | due date |
| status | TEXT | `open` / `paid` |
| description | TEXT | what it was for |

**Why it matters:** A vendor with an `open` invoice will not ship. Accounting must spot overdue bills (`due_date` < today) and get them paid, with approval, before ordering more.

---

## Working tables (added by the MCP server)

Created with `CREATE TABLE IF NOT EXISTS` in the **working copy only**, so a reset from `campus_customs.db` wipes them.

| table | fields | why it matters for the agents |
|---|---|---|
| `approval_requests` | id, kind (`invoice`/`rent`/`purchase_order`), ref_id, ticket_id, vendor_id, sku, size, qty, amount, payee, account, reason, requested_by, status (`pending`/`paid`/`rejected`), decided_by, decided_at, decision_note, expected_arrival, created_at | The handoff between agents and humans. Agents file requests here, and only a human's `approve_and_pay` turns one into money. Paid POs show up as "on order" in `check_stock`. |
| `drafts` | id, ticket_id, recipient, subject, body, author, status (`draft`), created_at | Every outgoing message waits here. Nothing is ever sent. |
| `ticket_log` | id, ticket_id, author, status, note, created_at | Shared memory for a ticket. Each agent records what it found, so reruns build on earlier work instead of repeating it. |

## Starting data snapshot

- **Cash:** checking = **$3,400.00**
- **Payments:** none
- **Invoices:** #501, Bulldog Print Co (vendor 1), $840.00, due 2026-08-28, **open and overdue**, "Rush reprint CC-TEE-WHITE S"
- **Lease:** #1, Chapel Street shop, Elm City Properties, $2,400.00/month, next due **2026-09-02**
- **Vendors:** 1 Bulldog Print Co (apparel reprint, 5 days) · 2 Elm City Gifts (mugs/small goods, 3 days) · 3 QuickShip CT (local courier, 1 day)

| sku | name | S | M | L | XL | OS | unit_cost | list_price |
|---|---|---|---|---|---|---|---|---|
| CC-HOOD-NAVY | Basic Hoodie Big Yale | 4 | 8 | 14 | 6 | | 22.00 | 58.00 |
| CC-TEE-WHITE | Classic Bulldog Tee | **0** | 5 | 3 | 2 | | 8.00 | 28.00 |
| CC-HAT-BLUE | Yale Cap | | | | | 40 | 6.00 | 22.00 |
| CC-MUG-CREST | Crest Mug | | | | | **0** | 3.50 | 14.00 |

---

## The three open tickets and how they link

### #101 — customer_order — Tauhid Zaman — "Bulldog tee"
- Wants **CC-TEE-WHITE, size S, qty 1**. Links: `invoice_id = 501`.
- `inventory`: CC-TEE-WHITE / S has **qty 0**, so it's out of stock.
- `vendors`: apparel restock comes from **Bulldog Print Co (id 1)**, with a 5-day lead time.
- `invoices`: #501 to Bulldog Print Co ($840) is **open and overdue** (due 08-28, today 08-31), so **Bulldog won't ship** until it is paid.
- Chain: Inventory (shortfall) → Accounting (pay #501, needs human approval) → Inventory (reorder) → Customer Service (draft an ETA message to Tauhid).

### #102 — rent_notice — Elm City Properties — "Rent due"
- Links: `lease_id = 1`.
- `leases`: $2,400 due **2026-09-02**, 2 days from today.
- `cash_accounts`: $3,400 is enough to cover it.
- Chain: Facilities (verify lease and amount) → Accounting (prepare the rent payment, needs human approval) → after payment, update `leases.next_due` and add a `payments` row.

### #103 — price_override — Yale AI Club — "Bulk hoodie discount"
- Wants **CC-HOOD-NAVY, size M, qty 20** at a bulk discount. No lease or invoice link.
- `inventory`: only **8** in size M, a **shortfall of 12**.
- `pricing`: cost $22, list $58, so $36 margin per unit (62%). Full order at list = $1,160, with cost of $440.
- `vendors`: restock also comes from **Bulldog Print Co**, which is blocked by the same open invoice #501.
- Chain: Inventory (shortfall + vendor) → Accounting (margin check for the discount, cost of a restock PO) → Boss (final call on the discount) → Customer Service (draft reply to the club).

### Cross-ticket constraint: cash
- Paying invoice #501 ($840) and rent ($2,400) costs **$3,240**, which leaves **$160**.
- Restocking 12 hoodies at $22 = **$264**, which is more than what's left. The agents (and Boss) have to prioritize and can't approve everything blindly.
- Invoice #501 blocks both #101 and #103.

---

## MCP tools (Problem 3)

Server: `mcp_server/server.py` (FastMCP). Every tool reads `data/campus_customs_new.db`, and all three are read-only for now.

### 1. `check_stock(sku, size, qty_needed=1)`
- **Reads:** `inventory` (row for that `sku` + `size`, plus the other sizes of the same SKU)
- **Unlocks:** **#101** (CC-TEE-WHITE / S / 1) and **#103** (CC-HOOD-NAVY / M / 20)
- **Why it's the right tool:** Both tickets ask whether a specific SKU and size can be filled. It returns `on_hand = 0, shortfall = 1` for Tauhid's tee and `on_hand = 8, shortfall = 12` for the AI Club's 20 hoodies, which tells Inventory that both orders need a restock before anyone promises a delivery.

### 2. `check_vendor_can_ship(vendor_id)`
- **Reads:** `vendors` (specialty, `lead_days`), `invoices` (open invoices for that vendor), `desk` (`date_today` for days overdue)
- **Unlocks:** **#101** and **#103**, since both restocks come from Bulldog Print Co (vendor 1, apparel reprint)
- **Why it's the right tool:** For vendor 1 it returns `can_ship = false` because invoice **#501 ($840, due 2026-08-28) is 3 days overdue**. That's exactly why the tee and hoodies can't be reordered yet. It sends the work to Accounting to get #501 approved and paid first, and once the vendor is clear it gives the arrival date (today + 5 days) for Customer Service to quote.

### 3. `get_lease_due(lease_id)`
- **Reads:** `leases` (rent, landlord, `next_due`), `desk` (`date_today`), `cash_accounts` (balance)
- **Unlocks:** **#102** (Elm City Properties rent notice, `lease_id = 1`)
- **Why it's the right tool:** The ticket is just an email saying "rent due in 2 days." This tool checks that claim against the lease record: $2,400 to Elm City Properties, due 2026-09-02, `days_until_due = 2`, and checking ($3,400) covers it. Facilities can then hand Accounting a verified amount to prepare for human approval.

---

## Agent team (Problem 5)

Built with **PydanticAI**. Every agent uses **`gpt-6-luna` through Portkey** (`backend/config.py`, hard-coded, with no env override), authenticated by `PORTKEY_API_KEY` from `.env`. Shop facts come **only** from the `campus-customs` MCP server over `data/campus_customs_new.db`. There is no second tools layer, and the backend never queries the database for shop facts. The only extra tool the agents have is `ask_agent`, which is for delegation, not data.

| Agent | File / prompt | Job | MCP tools it can call |
|---|---|---|---|
| **Boss** | `backend/agents/boss.py` · `backend/prompts/boss.md` | Reads each ticket, routes work, weighs cash across the whole board, sets the final status, and returns a structured `TicketDecision` | `list_open_tickets`, `get_ticket`, `add_ticket_note`, `set_ticket_status`, `get_cash_position`, `list_approval_requests` |
| **Inventory** | `backend/agents/inventory.py` · `backend/prompts/inventory.md` | Stock by SKU and size, shortfalls, which vendor can restock, and arrival dates | `get_ticket`, `add_ticket_note`, `check_stock`, `list_vendors`, `check_vendor_can_ship` |
| **Accounting** | `backend/agents/accounting.py` · `backend/prompts/accounting.md` | Cash, invoices and margins. Files payment and PO requests for human approval | `get_ticket`, `add_ticket_note`, `get_cash_position`, `get_invoice`, `check_margin`, `check_vendor_can_ship`, `get_lease_due`, `request_payment`, `request_purchase_order`, `list_approval_requests` |
| **Facilities** | `backend/agents/facilities.py` · `backend/prompts/facilities.md` | Leases and rent: checks a notice against the lease and hands rent to Accounting | `get_ticket`, `add_ticket_note`, `get_lease_due`, `get_cash_position`, `list_approval_requests` |
| **Customer Service** | `backend/agents/customer_service.py` · `backend/prompts/customer_service.md` | Drafts every outgoing message (customer, vendor, landlord). Drafts only | `get_ticket`, `add_ticket_note`, `check_stock`, `draft_message` |

**Full connectivity:** every agent also has `ask_agent(agent, request)` (`backend/agents/base.py`) and can delegate to any of the other four. A delegated agent runs its own loop and its answer comes back as the tool result.

**Agent loop:** `run_agent()` drives each agent with `Agent.iter()`. Every node (user prompt → model request → model response / tool calls → tool results → done) is written to the audit trail.

**Data types:** `backend/models.py` holds `TicketDecision` (the Boss output), `TeamDeps` (run id, ticket, agent, depth, shared budget), `RunBudget` and `AuditEvent`.

**Runner:** `python -m backend.run reset | work 101 | work --all | approvals | approve <id> --by "<name>" | reject <id> --by "<name>"`.

### Audit trail: `output/audit_trail.json`
One JSON array, **appended and never wiped** (load → append → atomic replace; an unreadable file is set aside, never deleted). Each event records `ts`, `run_id`, `ticket_id`, `agent`, `depth` (0 = Boss, 1+ = delegated), `event`, `detail`, `data` and `model`. Events:
- `ticket_start` / `ticket_done` (with the Boss's decision and the delegation chain)
- `agent_start` / `user_prompt` / `model_request` / `model_response` (model text, requested tool calls, token usage) / `agent_done` (output, request count, tokens)
- `tool_call` / `tool_result` / `tool_error` / `tool_blocked`: every MCP call with its exact arguments and result
- `delegate` / `delegate_result` / `delegate_refused`: who asked whom for what, and the answer
- `limit_hit` / `agent_error`
- `human_tool_call` / `human_tool_result`: human approvals and rejections

---

## MCP tools (all 18, final)

Server: `mcp_server/server.py`. Three working tables are created inside the **working copy only** if missing: `approval_requests`, `drafts` and `ticket_log`. A reset from `campus_customs.db` clears them.

| # | Tool | Tables | R/W | Used by | Ticket(s) |
|---|---|---|---|---|---|
| 0 | `list_tickets` | `tickets`, `desk` | R | dashboard (`GET /api/tickets`) | all |
| 1 | `list_open_tickets` | `tickets`, `desk` | R | Boss, runner | all |
| 2 | `get_ticket` | `tickets`, `ticket_log`, `drafts`, `approval_requests`, `desk` | R | all agents | all |
| 3 | `add_ticket_note` | `tickets`, `ticket_log` | W | all agents | all |
| 4 | `set_ticket_status` | `tickets`, `ticket_log` | W | **Boss only** | all |
| 5 | `check_stock` | `inventory`, `approval_requests` (paid POs = on order) | R | Inventory, Customer Service | 101, 103 |
| 6 | `list_vendors` | `vendors`, `invoices` | R | Inventory | 101, 103 |
| 7 | `check_vendor_can_ship` | `vendors`, `invoices`, `desk` | R | Inventory, Accounting | 101, 103 |
| 8 | `get_cash_position` | `cash_accounts`, `invoices`, `vendors`, `leases`, `approval_requests`, `desk` | R | Boss, Accounting, Facilities | all (shared cash) |
| 9 | `get_invoice` | `invoices`, `vendors`, `desk` | R | Accounting | 101 (invoice 501) |
| 10 | `check_margin` | `pricing` | R | Accounting | 103 |
| 11 | `get_lease_due` | `leases`, `cash_accounts`, `desk` | R | Facilities, Accounting | 102 |
| 12 | `request_payment` | `invoices`, `vendors`, `leases`, `cash_accounts`, `tickets`, `approval_requests` | W | Accounting | 101 (invoice 501), 102 (rent) |
| 13 | `request_purchase_order` | `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `tickets`, `approval_requests`, `desk` | W | Accounting | 101, 103 (restock) |
| 14 | `list_approval_requests` | `approval_requests` | R | Boss, Accounting, Facilities | all |
| 15 | `draft_message` | `tickets`, `drafts` | W | Customer Service | all |
| 16 | `approve_and_pay` | `approval_requests`, `cash_accounts`, `payments`, `invoices`, `leases`, `vendors`, `ticket_log`, `desk` | W | **Human only** | 101, 102, 103 |
| 17 | `reject_request` | `approval_requests`, `ticket_log` | W | **Human only** | any |

---

## Safety

### Guardrails a real business would want (agents touching real customers and real money)
- **Humans hold the money.** Agents can only *request* payments or POs. `approve_and_pay` and `reject_request` are filtered out of every agent's toolset and blocked again in the MCP call hook. The server rejects an agent name as approver. Each payment row records the human's name in `payments.approved_by`.
- **Amounts come from the database, not the model.** `request_payment` and `request_purchase_order` look up the amount and payee from `invoices`, `leases` and `pricing`. An agent can't type in a different number or payee.
- **No negative balances.** Requests are refused if they exceed cash minus already-pending requests, and `approve_and_pay` refuses again at payment time. No money comes in.
- **Business rules in code, not just prompts.** POs to a vendor with an open invoice are refused. Duplicate pending requests are refused. Only the Boss can set a ticket's status. A paid PO is recorded as placed and shows as on order, so nobody orders twice.
- **Identity can't be spoofed.** The MCP call hook overwrites `author` / `requested_by` with the real calling agent, so the audit trail and ticket log show who actually did what.
- **Nothing leaves the building.** There's no send tool. `draft_message` only saves drafts, and a human sends them. Customer Service is told never to reveal internal cash or approvals to customers.
- **Least privilege.** Each agent sees only the MCP tools its role needs.
- **Full audit.** Every model step, tool call, result, delegation and human action is appended to `output/audit_trail.json` and never wiped.
- **Safe test data.** Agents only touch the working copy, and `python -m backend.run reset` restores it from the untouched original.
- **Secrets.** `PORTKEY_API_KEY` is loaded from `.env`, never hard-coded or logged. `.env` is in `.gitignore`.
- **Would add for production:** spend limits per approver, two-person approval above a threshold, a vendor and payee allow-list, PII redaction in logs, rate limits on drafts, and alerts on refused or blocked calls.

### Limits that keep token use in check (`backend/config.py`)
- **One model only:** `gpt-6-luna` for every agent.
- **Delegation depth ≤ 2** (Boss → specialist → specialist). Deeper requests are refused with a message telling the agent to finish.
- **≤ 8 delegations per ticket**, shared across the whole team for that ticket. Self-delegation is refused.
- **Request caps per agent loop:** Boss 14 model calls, specialists 8.
- **≤ 80,000 tokens per agent run** (`UsageLimits.total_tokens_limit`). Hitting a limit is caught, logged as `limit_hit`, and returned as a short message instead of crashing the ticket.
- **Compact tool results:** tools return only the fields needed, and audit fields are clipped to 2,000 characters.
- Prompts tell agents to check the ticket log first and not repeat work or questions.

---

## Backend routes (Problem 7)

`backend/main.py` (FastAPI). Start it from `backend/` with `uvicorn main:app --reload --port 8000` → http://localhost:8000 (interactive docs at `/docs`). Every route reaches shop data through the MCP server. CORS is open to the Vite dashboard on `localhost:5173`.

| Method · URL | What it does |
|---|---|
| `GET /api/tickets` | All tickets with `status`, `is_open` and `is_resolved` (MCP `list_tickets`). |
| `GET /api/tickets/{ticket_id}` | One ticket with its log, drafts and approval requests (MCP `get_ticket`). |
| `POST /api/tickets/{ticket_id}/run` | Runs the agent team (Boss first) on that ticket in the background and returns a `run_id`. `?wait=true` blocks until the decision is ready. Returns 409 if a run is already going. |
| `GET /api/runs/{run_id}` | Status of a run (queued, running, done, error) plus the Boss's `TicketDecision`. |
| `GET /api/events?after=&limit=&ticket_id=&run_id=` | Recent audit-trail events: what each agent said, the tools it called with args and results, and delegations. `after` lets the board fetch only new events. |
| `GET /api/approvals?status=pending` | Payment and purchase-order requests the agents prepared. |
| `POST /api/approvals/{request_id}/approve` `{approved_by}` | A human clicked Approve. This is the **only route that changes cash**: it pays through MCP `approve_and_pay`, refuses agents as approvers and refuses negative balances, and writes `payments`, `cash_accounts` and the invoice, lease or PO. |
| `POST /api/approvals/{request_id}/reject` `{decided_by, note}` | A human clicked Reject. No money moves. |
| `GET /api/cash` | Current checking balance from `cash_accounts`, plus `pending_total` and `cash_after_pending`. |
| `POST /api/reset` | Copies `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run. Refused while a run is going. Logged in the audit trail, which is kept. |
| `GET /api/health` | Server is up, model name, and whether a run is in progress. |

---

## Dashboard (Problem 8)

`frontend/` (React + Vite + TypeScript). Start it with `npm run dev`; it opens at http://localhost:5173, or the next free port. It calls the backend at `VITE_API_URL` (`http://localhost:8000`), and the backend's CORS allows local Vite ports. Full design rationale is in `output/design.md`.

| Area | What it shows | Routes it calls |
|---|---|---|
| **Ticket board** (left) | All tickets, a status pill (Open, Agents working…, Needs you, Resolved), a RESOLVED stamp, and an "x/3 resolved" bar | `GET /api/tickets` |
| **Up close** (left) | The customer's words, **Start the team** / **Hand back to the team**, and the ticket log | `GET /api/tickets/{id}`, `POST /api/tickets/{id}/run`, `GET /api/runs/{run_id}` |
| **The floor** (center) | Five Labubu agents, each with its own accessory and color. Live speech bubbles show what each is saying or doing. Delegation lines glow while a handoff is open. Agents that weren't needed are greyed out ("sat this one out"). | `GET /api/events` (polled every 1.2s while running) |
| **Desk chatter** | Timeline of every model step, tool call with args, result, and delegation, indented by depth | `GET /api/events` |
| **Who did what** | The Boss's decision and next step, then one card per agent with who called it, who it handed off to, tool chips and its last words. Also the drafts, marked "never sent" | `GET /api/events`, `GET /api/tickets/{id}` |
| **Checking** (right) | A register-style balance that rolls down and shakes on a payment, a free vs. pending bar, and a receipt tape of approved payments | `GET /api/cash`, `GET /api/approvals?status=paid` |
| **Needs your signature** (right) | Requests shown as paper checks, a "Signing as" name field, and **Approve & pay** / **Reject**. These are the only money controls | `GET /api/approvals`, `POST /api/approvals/{id}/approve`, `POST /api/approvals/{id}/reject` |
| **↺ Reset shop** | Restores the original database | `POST /api/reset` |

---

## Full run results (Problem 9)

Reset at 15:27 on 2026-10-13. Starting checking **$3,400.00**, ending **$152.00**, which matches `cash_accounts`. All 3 tickets are **resolved**. Details are in `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, `output/resolved_board.html` and `output/audit_trail.json` (this run starts at the `database_reset` event at 15:27:05).

| Ticket | Runs | First call | Delegations (all runs) | Human approvals | Cash |
|---|---|---|---|---|---|
| 101 tee | 4 | Inventory | Boss→Inventory, Boss→Accounting, Boss→Customer Service, Accounting↔Inventory | #1 invoice 501 $840 · #3 PO 1 tee $8 | −$848 |
| 102 rent | 2 | Facilities | Boss→Facilities, Facilities→Accounting | #2 rent $2,400 | −$2,400 |
| 103 hoodies | 1 | Inventory | Boss→Inventory, Boss→Accounting, Boss→Customer Service, Customer Service→Accounting | none | $0 |

`$3,400.00 − $840.00 − $2,400.00 − $8.00 = $152.00`

**What the run taught us**
- Routing followed the plan: no ticket used all four specialists, Facilities only worked on rent, and the guardrails held. Requests were filed, never paid, by agents. The PO waited until invoice 501 was paid. No duplicate requests were filed. The discount never went below cost.
- **Tool gap fixed mid-run:** after the $8 PO was paid, the Boss wouldn't resolve 101 because nothing showed the order as placed. `check_stock` now returns `on_order` / `placed_orders`, approving a PO logs "purchase order placed", and the Boss prompt treats a paid PO as placed, since the shop date doesn't move forward.
- The depth limit refused two specialist-to-specialist handoffs on 101 (`delegate_refused` in the audit trail), which kept the delegation chain short.
- Token use per ticket run ranged from about 11k (102's Boss-only close) to about 75k (101 run 2), all within the per-agent cap of 80k.
