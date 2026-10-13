# Campus Customs MCP Server

This is the shared toolbox for the Campus Customs multi-agent team, and the **only** way the agents reach shop data. Every agent (Boss, Inventory, Accounting, Facilities, Customer Service) reads and writes the shop through these tools instead of writing its own SQL. That keeps every agent on the same rules and stops them from inventing data. If a record doesn't exist, the tool returns an error rather than a guess.

Built with [FastMCP](https://gofastmcp.com).

## Database

- **Uses:** `data/campus_customs_new.db`, the working copy. Tools read and update this file.
- **Never touches:** `data/campus_customs.db`, the original. Reset with `python -m backend.run reset`.
- "Today" for the shop is `desk.date_today`, not the real clock.
- On first use the server adds three working tables to the working copy: `approval_requests` (payments and POs waiting on a human), `drafts` (unsent messages) and `ticket_log` (ticket history).

## Rules the tools enforce

- Payment and PO amounts and payees are read from the database, never taken from the caller.
- Agents can only **request** payments. Money moves only through `approve_and_pay`, which needs a named human and refuses to make any balance negative.
- A vendor with an open invoice can't get a purchase order.
- There is no send tool. Messages are saved as drafts.

## Tools (18)

| Tool | Tables | What it does |
|---|---|---|
| `list_tickets()` | tickets, desk | Every ticket with is_open / is_resolved flags (dashboard board) |
| `list_open_tickets()` | tickets, desk | Every ticket not resolved or declined |
| `get_ticket(ticket_id)` | tickets, ticket_log, drafts, approval_requests, desk | One ticket with its history, drafts and requests |
| `add_ticket_note(ticket_id, author, note)` | tickets, ticket_log | Add a work note |
| `set_ticket_status(ticket_id, status, note, author)` | tickets, ticket_log | Change status (Boss only) |
| `check_stock(sku, size, qty_needed)` | inventory, approval_requests | On hand, shortfall, units on order (paid POs) with arrival, other sizes |
| `list_vendors()` | vendors, invoices | Specialty, lead time, can ship now? |
| `check_vendor_can_ship(vendor_id)` | vendors, invoices, desk | Open invoices, days overdue, arrival date |
| `get_cash_position()` | cash_accounts, invoices, vendors, leases, approval_requests, desk | Cash, pending requests, cash after pending, bills and rent coming up |
| `get_invoice(invoice_id)` | invoices, vendors, desk | One invoice and how overdue it is |
| `check_margin(sku, qty, discount_pct)` | pricing | Revenue, cost, profit, margin, break-even discount |
| `get_lease_due(lease_id)` | leases, cash_accounts, desk | Rent, landlord, due date, days until due |
| `request_payment(kind, ref_id, ticket_id, reason, requested_by)` | invoices, vendors, leases, cash_accounts, tickets, approval_requests | Request approval to pay an invoice or rent (doesn't pay) |
| `request_purchase_order(vendor_id, sku, size, qty, ticket_id, reason, requested_by)` | vendors, invoices, inventory, pricing, cash_accounts, tickets, approval_requests, desk | Request approval for a restock (doesn't order) |
| `list_approval_requests(status)` | approval_requests | Pending, paid, rejected or all requests |
| `draft_message(ticket_id, recipient, subject, body, author)` | tickets, drafts | Save an unsent draft |
| `approve_and_pay(request_id, approved_by)` | approval_requests, cash_accounts, payments, invoices, leases, vendors, ticket_log, desk | **Human only.** Pay, update the balance, record the payment, mark the invoice paid or move rent forward |
| `reject_request(request_id, decided_by, note)` | approval_requests, ticket_log | **Human only.** Reject; no money moves |

The two human-only tools are filtered out of every agent's toolset by the backend.

## Run

```bash
pip install -r requirements.txt
python mcp_server/server.py
```

Claude Code loads it from `.mcp.json` at the project root, and the agent backend launches it over stdio.
