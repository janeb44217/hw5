"""Campus Customs MCP server.

The one and only shop-tools layer. Every agent (and the human approval path)
reads and writes the shop through these tools, which all point at the working
copy data/campus_customs_new.db; the original campus_customs.db is never touched.

Rules enforced here, not just in prompts:
  - "Today" is desk.date_today, never the real clock.
  - Tools only report what is in the database; missing records return an error.
  - Amounts for payments and purchase orders are looked up from the database,
    never taken from the caller.
  - Agents can only *request* payments. Money moves only through
    approve_and_pay, which needs a named human approver and refuses any payment
    that would push a cash balance below zero.
  - A vendor with an open invoice cannot get a purchase order.
  - Messages are saved as drafts only; there is no send tool.
"""

import sqlite3
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = {"open", "in_progress", "waiting_approval", "resolved", "declined"}
PAYMENT_KINDS = {"invoice", "rent"}

mcp = FastMCP("campus-customs")

# Working tables the shop needs on top of the original schema. Created in the
# working copy only, so resetting from campus_customs.db clears them too.
_EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,              -- invoice | rent | purchase_order
    ref_id INTEGER,                  -- invoices.id / leases.id / NULL for a PO
    ticket_id INTEGER,
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    amount REAL NOT NULL,
    payee TEXT NOT NULL,
    account TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,            -- pending | paid | rejected
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    expected_arrival TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_log (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    status TEXT,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_EXTRA_SCHEMA)
    return conn


def _shop_today(conn: sqlite3.Connection) -> date:
    """The shop's 'today' comes from desk.date_today, never the real clock."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return date.fromisoformat(row["date_today"])


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _add_days(d: date, days: int) -> date:
    return date.fromordinal(d.toordinal() + days)


def _add_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, amount, due_date, description FROM invoices "
        "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
        (vendor_id,),
    ).fetchall()


def _ticket_exists(conn: sqlite3.Connection, ticket_id: int) -> bool:
    return conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is not None


def _check_agent(name: str) -> str | None:
    if name not in AGENT_NAMES:
        return f"Unknown agent {name!r}; use one of {sorted(AGENT_NAMES)}."
    return None


# ---------------------------------------------------------------- tickets

def list_open_tickets() -> dict:
    """List every ticket that is not resolved or declined, with the shop's today.

    Reads tickets and desk. The Boss uses this to see the board.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status NOT IN ('resolved', 'declined') ORDER BY id"
        ).fetchall()
    return {"shop_today": today.isoformat(), "tickets": [dict(r) for r in rows]}


def list_tickets() -> dict:
    """List every ticket on the board, whatever its status, with open/resolved flags.

    Reads tickets and desk. Used by the dashboard's ticket board.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    tickets = []
    for r in rows:
        t = dict(r)
        t["is_open"] = t["status"] not in ("resolved", "declined")
        t["is_resolved"] = t["status"] == "resolved"
        tickets.append(t)
    return {"shop_today": today.isoformat(), "tickets": tickets}


def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with its full history log, drafts, and approval requests.

    Reads tickets, ticket_log, drafts, approval_requests, and desk.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"error": f"No ticket with id={ticket_id}."}
        log = conn.execute(
            "SELECT author, status, note, created_at FROM ticket_log WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
        drafts = conn.execute(
            "SELECT id, recipient, subject, body, author, status FROM drafts WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
        requests = conn.execute(
            "SELECT id, kind, ref_id, amount, payee, status, decided_by, expected_arrival "
            "FROM approval_requests WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
    return {
        "shop_today": today.isoformat(),
        "ticket": dict(ticket),
        "log": [dict(r) for r in log],
        "drafts": [dict(r) for r in drafts],
        "approval_requests": [dict(r) for r in requests],
    }


def add_ticket_note(ticket_id: int, author: str, note: str) -> dict:
    """Add a work note to a ticket's history without changing its status.

    Writes ticket_log. Any agent can use this to record findings for the others.
    """
    if err := _check_agent(author):
        return {"error": err}
    with _connect() as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"No ticket with id={ticket_id}."}
        conn.execute(
            "INSERT INTO ticket_log (ticket_id, author, status, note, created_at) VALUES (?, ?, NULL, ?, ?)",
            (ticket_id, author, note, _now()),
        )
    return {"ticket_id": ticket_id, "logged": True}


def set_ticket_status(ticket_id: int, status: str, note: str, author: str = "boss") -> dict:
    """Change a ticket's status and log why. Only the Boss makes this call.

    Writes tickets.status and ticket_log. Allowed statuses: open, in_progress,
    waiting_approval, resolved, declined.
    """
    if author != "boss":
        return {"error": "Only the boss can change a ticket's status."}
    if status not in TICKET_STATUSES:
        return {"error": f"Invalid status {status!r}; use one of {sorted(TICKET_STATUSES)}."}
    with _connect() as conn:
        row = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"error": f"No ticket with id={ticket_id}."}
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute(
            "INSERT INTO ticket_log (ticket_id, author, status, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, author, status, note, _now()),
        )
    return {"ticket_id": ticket_id, "old_status": row["status"], "new_status": status}


# ---------------------------------------------------------------- inventory

def check_stock(sku: str, size: str, qty_needed: int = 1) -> dict:
    """Check how many units of a SKU in a given size are on hand.

    Reads inventory and approval_requests. Returns on-hand qty, the shortfall
    against qty_needed, units already on order (approved + paid purchase orders,
    i.e. placed with the vendor) with expected arrival, and other sizes in stock.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            return {"error": f"No inventory record for sku={sku!r}, size={size!r}."}

        other_sizes = conn.execute(
            "SELECT size, qty FROM inventory WHERE sku = ? AND size != ? ORDER BY size",
            (sku, size),
        ).fetchall()
        # Approved + paid purchase orders are placed with the vendor; stock arrives later.
        orders = conn.execute(
            "SELECT id, qty, payee, expected_arrival, decided_by FROM approval_requests "
            "WHERE kind = 'purchase_order' AND status = 'paid' AND sku = ? AND size = ? ORDER BY id",
            (sku, size),
        ).fetchall()

    on_hand = row["qty"]
    on_order = sum(o["qty"] for o in orders)
    return {
        "sku": row["sku"],
        "name": row["name"],
        "size": row["size"],
        "location": row["location"],
        "on_hand": on_hand,
        "qty_needed": qty_needed,
        "shortfall": max(qty_needed - on_hand, 0),
        "can_fill_from_stock": on_hand >= qty_needed,
        "on_order": on_order,
        "placed_orders": [
            {"request_id": o["id"], "qty": o["qty"], "vendor": o["payee"],
             "expected_arrival": o["expected_arrival"], "approved_by": o["decided_by"]}
            for o in orders
        ],
        "shortfall_after_orders": max(qty_needed - on_hand - on_order, 0),
        "other_sizes": {r["size"]: r["qty"] for r in other_sizes},
    }


def list_vendors() -> dict:
    """List every vendor with specialty, lead time, and whether they can ship now.

    Reads vendors and invoices. Use it to pick who can restock a product.
    """
    with _connect() as conn:
        vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        result = []
        for v in vendors:
            open_inv = _open_invoices(conn, v["id"])
            result.append({
                **dict(v),
                "can_ship": not open_inv,
                "open_invoice_ids": [i["id"] for i in open_inv],
            })
    return {"vendors": result}


def check_vendor_can_ship(vendor_id: int) -> dict:
    """Check whether a vendor will ship new product right now.

    Reads vendors, invoices, and desk. A vendor will not ship while they have
    any open (unpaid) invoice. Returns every open invoice with days overdue,
    the lead time, and the expected arrival date if an order were placed today.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"error": f"No vendor with id={vendor_id}."}
        open_invoices = _open_invoices(conn, vendor_id)

    invoices = []
    for inv in open_invoices:
        days_overdue = (today - date.fromisoformat(inv["due_date"])).days
        invoices.append({
            "invoice_id": inv["id"],
            "amount": inv["amount"],
            "due_date": inv["due_date"],
            "days_overdue": max(days_overdue, 0),
            "overdue": days_overdue > 0,
            "description": inv["description"],
        })

    can_ship = not invoices
    result = {
        "vendor_id": vendor["id"],
        "name": vendor["name"],
        "specialty": vendor["specialty"],
        "lead_days": vendor["lead_days"],
        "shop_today": today.isoformat(),
        "can_ship": can_ship,
        "open_invoices": invoices,
        "total_open_owed": round(sum(i["amount"] for i in invoices), 2),
    }
    if can_ship:
        result["arrival_if_ordered_today"] = _add_days(today, vendor["lead_days"]).isoformat()
    else:
        result["blocked_reason"] = "Vendor has open unpaid invoice(s); they will not ship until paid."
    return result


# ---------------------------------------------------------------- money

def get_cash_position() -> dict:
    """Show cash on hand, what is already promised, and what is still owed.

    Reads cash_accounts, invoices, leases, approval_requests, and desk. Use it
    before asking a human to approve anything so requests never exceed cash.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        accounts = conn.execute("SELECT name, balance, date FROM cash_accounts").fetchall()
        pending = conn.execute(
            "SELECT id, kind, amount, payee, account FROM approval_requests WHERE status = 'pending' ORDER BY id"
        ).fetchall()
        invoices = conn.execute(
            "SELECT i.id, v.name AS vendor, i.amount, i.due_date FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
        ).fetchall()
        leases = conn.execute("SELECT id, landlord, monthly_rent, next_due FROM leases ORDER BY next_due").fetchall()

    total_cash = round(sum(a["balance"] for a in accounts), 2)
    pending_total = round(sum(p["amount"] for p in pending), 2)
    return {
        "shop_today": today.isoformat(),
        "accounts": [dict(a) for a in accounts],
        "total_cash": total_cash,
        "pending_approvals": [dict(p) for p in pending],
        "pending_total": pending_total,
        "cash_after_pending": round(total_cash - pending_total, 2),
        "open_invoices": [
            {**dict(i), "overdue": date.fromisoformat(i["due_date"]) < today} for i in invoices
        ],
        "upcoming_rent": [
            {**dict(l), "days_until_due": (date.fromisoformat(l["next_due"]) - today).days} for l in leases
        ],
        "note": "No money comes in; every approved payment only reduces cash.",
    }


def get_invoice(invoice_id: int) -> dict:
    """Look up one invoice with its vendor and how overdue it is.

    Reads invoices, vendors, and desk.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        inv = conn.execute(
            "SELECT i.*, v.name AS vendor_name, v.specialty FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
    if inv is None:
        return {"error": f"No invoice with id={invoice_id}."}
    days_overdue = (today - date.fromisoformat(inv["due_date"])).days
    return {
        **dict(inv),
        "shop_today": today.isoformat(),
        "overdue": inv["status"] == "open" and days_overdue > 0,
        "days_overdue": max(days_overdue, 0) if inv["status"] == "open" else 0,
    }


def check_margin(sku: str, qty: int, discount_pct: float = 0.0) -> dict:
    """Work out revenue, cost, and margin for selling qty units at a discount.

    Reads pricing. discount_pct is a percent off list price (e.g. 15 for 15%).
    Also reports the largest discount that still breaks even.
    """
    if qty <= 0:
        return {"error": "qty must be positive."}
    if not 0 <= discount_pct < 100:
        return {"error": "discount_pct must be between 0 and 100."}
    with _connect() as conn:
        p = conn.execute("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if p is None:
        return {"error": f"No pricing for sku={sku!r}."}

    unit_price = round(p["list_price"] * (1 - discount_pct / 100), 2)
    revenue = round(unit_price * qty, 2)
    cost = round(p["unit_cost"] * qty, 2)
    profit = round(revenue - cost, 2)
    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": p["unit_cost"],
        "list_price": p["list_price"],
        "discount_pct": discount_pct,
        "unit_price_after_discount": unit_price,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "margin_pct": round(profit / revenue * 100, 1) if revenue else None,
        "list_margin_pct": round((p["list_price"] - p["unit_cost"]) / p["list_price"] * 100, 1),
        "break_even_discount_pct": round((1 - p["unit_cost"] / p["list_price"]) * 100, 1),
        "sells_below_cost": unit_price < p["unit_cost"],
    }


def get_lease_due(lease_id: int) -> dict:
    """Look up a lease's rent amount, landlord, and next due date.

    Reads leases, cash_accounts, and desk. Reports days until due and whether
    each cash account covers the rent.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"error": f"No lease with id={lease_id}."}
        accounts = conn.execute("SELECT name, balance FROM cash_accounts").fetchall()

    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
    return {
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "shop_today": today.isoformat(),
        "days_until_due": days_until_due,
        "overdue": days_until_due < 0,
        "notes": lease["notes"],
        "cash_accounts": {a["name"]: a["balance"] for a in accounts},
        "cash_covers_rent": {a["name"]: a["balance"] >= lease["monthly_rent"] for a in accounts},
    }


def request_payment(kind: str, ref_id: int, ticket_id: int, reason: str,
                    requested_by: str = "accounting", account: str = "checking") -> dict:
    """Ask a human to approve paying an invoice or a lease's rent. Does NOT pay.

    kind is 'invoice' (ref_id = invoices.id) or 'rent' (ref_id = leases.id).
    The amount and payee are read from the database. Writes approval_requests.
    Refuses duplicates, already-paid invoices, and requests that would exceed
    the cash left after other pending approvals.
    """
    if err := _check_agent(requested_by):
        return {"error": err}
    if kind not in PAYMENT_KINDS:
        return {"error": f"kind must be one of {sorted(PAYMENT_KINDS)}; use request_purchase_order for restocks."}

    with _connect() as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"No ticket with id={ticket_id}."}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            return {"error": f"No cash account named {account!r}."}

        if kind == "invoice":
            row = conn.execute(
                "SELECT i.amount, i.status, v.name AS payee FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                return {"error": f"No invoice with id={ref_id}."}
            if row["status"] != "open":
                return {"error": f"Invoice {ref_id} is already {row['status']}."}
        else:
            row = conn.execute(
                "SELECT monthly_rent AS amount, landlord AS payee FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if row is None:
                return {"error": f"No lease with id={ref_id}."}

        dup = conn.execute(
            "SELECT id FROM approval_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if dup is not None:
            return {"error": f"A pending approval request already exists for this {kind}: request {dup['id']}."}

        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM approval_requests WHERE status = 'pending' AND account = ?",
            (account,),
        ).fetchone()["t"]
        available = round(acct["balance"] - pending, 2)
        if row["amount"] > available:
            return {
                "error": "Not enough uncommitted cash for this request.",
                "amount": row["amount"],
                "balance": acct["balance"],
                "already_pending": pending,
                "available": available,
            }

        cur = conn.execute(
            "INSERT INTO approval_requests (kind, ref_id, ticket_id, amount, payee, account, reason, "
            "requested_by, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (kind, ref_id, ticket_id, row["amount"], row["payee"], account, reason, requested_by, _now()),
        )
    return {
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "ref_id": ref_id,
        "amount": row["amount"],
        "payee": row["payee"],
        "account": account,
        "cash_available_after_this": round(available - row["amount"], 2),
        "next_step": "A human must approve this in the dashboard before any money moves.",
    }


def request_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                           reason: str, requested_by: str = "accounting",
                           account: str = "checking") -> dict:
    """Ask a human to approve a restock purchase order. Does NOT order or pay.

    Cost is qty x pricing.unit_cost. Refuses if the vendor has any open invoice
    (they will not ship), if the SKU/size does not exist, or if the cost exceeds
    cash left after other pending approvals. Writes approval_requests.
    """
    if err := _check_agent(requested_by):
        return {"error": err}
    if qty <= 0:
        return {"error": "qty must be positive."}

    with _connect() as conn:
        today = _shop_today(conn)
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"No ticket with id={ticket_id}."}
        vendor = conn.execute("SELECT id, name, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"error": f"No vendor with id={vendor_id}."}
        open_inv = _open_invoices(conn, vendor_id)
        if open_inv:
            return {
                "error": f"{vendor['name']} will not ship while invoice(s) {[i['id'] for i in open_inv]} are open. "
                         "Get the invoice paid first.",
            }
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"error": f"No inventory record for sku={sku!r}, size={size!r}."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"error": f"No pricing for sku={sku!r}."}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            return {"error": f"No cash account named {account!r}."}

        amount = round(price["unit_cost"] * qty, 2)
        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM approval_requests WHERE status = 'pending' AND account = ?",
            (account,),
        ).fetchone()["t"]
        available = round(acct["balance"] - pending, 2)
        if amount > available:
            return {
                "error": "Not enough uncommitted cash for this purchase order.",
                "amount": amount,
                "balance": acct["balance"],
                "already_pending": pending,
                "available": available,
            }

        arrival = _add_days(today, vendor["lead_days"]).isoformat()
        cur = conn.execute(
            "INSERT INTO approval_requests (kind, ref_id, ticket_id, vendor_id, sku, size, qty, amount, payee, "
            "account, reason, requested_by, status, expected_arrival, created_at) "
            "VALUES ('purchase_order', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (ticket_id, vendor_id, sku, size, qty, amount, vendor["name"], account, reason,
             requested_by, arrival, _now()),
        )
    return {
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": "purchase_order",
        "vendor": vendor["name"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": price["unit_cost"],
        "amount": amount,
        "expected_arrival_if_approved_today": arrival,
        "cash_available_after_this": round(available - amount, 2),
        "next_step": "A human must approve this in the dashboard before the order is placed.",
    }


def list_approval_requests(status: str = "pending") -> dict:
    """List approval requests by status: pending, paid, rejected, or all.

    Reads approval_requests.
    """
    with _connect() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM approval_requests ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM approval_requests WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
    return {"status": status, "requests": [dict(r) for r in rows]}


# ---------------------------------------------------------------- human-only

def approve_and_pay(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve a pending request and move the money.

    Refuses agents as approvers and refuses any payment that would make the
    cash balance negative. On success it writes payments, lowers
    cash_accounts.balance, and marks the invoice paid / moves the lease's
    next_due forward one month / records the purchase order.
    """
    approver = (approved_by or "").strip()
    if not approver or approver.lower() in AGENT_NAMES:
        return {"error": "approve_and_pay needs a named human approver, not an agent."}

    with _connect() as conn:
        today = _shop_today(conn)
        req = conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"error": f"No approval request with id={request_id}."}
        if req["status"] != "pending":
            return {"error": f"Request {request_id} is already {req['status']}."}

        acct = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (req["account"],)
        ).fetchone()
        if acct is None:
            return {"error": f"No cash account named {req['account']!r}."}
        if req["amount"] > acct["balance"]:
            return {
                "error": "Refused: not enough cash. Balances may never go negative.",
                "amount": req["amount"],
                "balance": acct["balance"],
            }

        extra = {}
        if req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"error": f"Invoice {req['ref_id']} is not open; nothing to pay."}
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            extra["invoice_status"] = "paid"
            ref_id = req["ref_id"]
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            if lease is None:
                return {"error": f"No lease with id={req['ref_id']}."}
            new_due = _add_month(date.fromisoformat(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, req["ref_id"]))
            extra.update(paid_period_due=lease["next_due"], lease_next_due=new_due)
            ref_id = req["ref_id"]
        else:  # purchase_order
            if _open_invoices(conn, req["vendor_id"]):
                return {"error": f"Vendor {req['payee']} has an open invoice again; they will not ship."}
            arrival = None
            vendor = conn.execute("SELECT lead_days FROM vendors WHERE id = ?", (req["vendor_id"],)).fetchone()
            if vendor is not None:
                arrival = _add_days(today, vendor["lead_days"]).isoformat()
            conn.execute(
                "UPDATE approval_requests SET expected_arrival = ? WHERE id = ?", (arrival, request_id)
            )
            extra.update(sku=req["sku"], size=req["size"], qty=req["qty"], expected_arrival=arrival,
                         order_status="placed with vendor")
            ref_id = request_id

        new_balance = round(acct["balance"] - req["amount"], 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today.isoformat(), req["account"]),
        )
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], ref_id, req["amount"], req["account"], today.isoformat(), approver),
        )
        conn.execute(
            "UPDATE approval_requests SET status = 'paid', decided_by = ?, decided_at = ? WHERE id = ?",
            (approver, _now(), request_id),
        )
        if req["ticket_id"] is not None:
            note = f"Approved and paid request {request_id}: {req['kind']} ${req['amount']:.2f} to {req['payee']}."
            if req["kind"] == "purchase_order":
                note += (f" Purchase order placed with {req['payee']}: {req['qty']} x {req['sku']} size {req['size']},"
                         f" expected arrival {extra['expected_arrival']}.")
            conn.execute(
                "INSERT INTO ticket_log (ticket_id, author, status, note, created_at) VALUES (?, ?, NULL, ?, ?)",
                (req["ticket_id"], f"human:{approver}", note, _now()),
            )
    return {
        "request_id": request_id,
        "status": "paid",
        "payment_id": cur.lastrowid,
        "kind": req["kind"],
        "amount": req["amount"],
        "payee": req["payee"],
        "approved_by": approver,
        "paid_at": today.isoformat(),
        "account": req["account"],
        "new_balance": new_balance,
        **extra,
    }


def reject_request(request_id: int, decided_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Reject a pending approval request; no money moves.

    Writes approval_requests and ticket_log.
    """
    decider = (decided_by or "").strip()
    if not decider or decider.lower() in AGENT_NAMES:
        return {"error": "reject_request needs a named human, not an agent."}
    with _connect() as conn:
        req = conn.execute("SELECT status, ticket_id FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"error": f"No approval request with id={request_id}."}
        if req["status"] != "pending":
            return {"error": f"Request {request_id} is already {req['status']}."}
        conn.execute(
            "UPDATE approval_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? "
            "WHERE id = ?",
            (decider, _now(), note, request_id),
        )
        if req["ticket_id"] is not None:
            conn.execute(
                "INSERT INTO ticket_log (ticket_id, author, status, note, created_at) VALUES (?, ?, NULL, ?, ?)",
                (req["ticket_id"], f"human:{decider}", f"Rejected request {request_id}. {note}".strip(), _now()),
            )
    return {"request_id": request_id, "status": "rejected", "decided_by": decider}


# ---------------------------------------------------------------- messages

def draft_message(ticket_id: int, recipient: str, subject: str, body: str,
                  author: str = "customer_service") -> dict:
    """Save a message as a DRAFT on the board. Nothing is ever sent.

    Writes drafts. Use for customer replies, vendor notes, and landlord replies.
    """
    if err := _check_agent(author):
        return {"error": err}
    with _connect() as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"No ticket with id={ticket_id}."}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, author, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'draft', ?)",
            (ticket_id, recipient, subject, body, author, _now()),
        )
    return {"draft_id": cur.lastrowid, "status": "draft", "sent": False,
            "note": "Saved on the board only. A human sends it."}


AGENT_TOOLS = (
    list_tickets, list_open_tickets, get_ticket, add_ticket_note, set_ticket_status,
    check_stock, list_vendors, check_vendor_can_ship,
    get_cash_position, get_invoice, check_margin, get_lease_due,
    request_payment, request_purchase_order, list_approval_requests,
    draft_message,
)
HUMAN_ONLY_TOOLS = (approve_and_pay, reject_request)

for _tool in AGENT_TOOLS + HUMAN_ONLY_TOOLS:
    mcp.tool(_tool)


if __name__ == "__main__":
    mcp.run(show_banner=False)
