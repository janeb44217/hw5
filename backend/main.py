"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:
    uvicorn main:app --reload --port 8000

Shop facts and every change to the database go through the campus-customs MCP
server (human_call for the human side, the agent team for the agents). The only
route that moves money is the human approval route.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# `uvicorn main:app` runs this file as a top-level module from backend/;
# put the project root on the path so the backend package imports normally.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import audit  # noqa: E402
from backend.config import AUDIT_TRAIL, MODEL_NAME  # noqa: E402
from backend.mcp_link import human_call  # noqa: E402
from backend.models import TeamDeps  # noqa: E402
from backend.run import human_action, reset_db, work_tickets  # noqa: E402

app = FastAPI(title="Campus Customs Multi-Agent Operations", version="1.0")

app.add_middleware(
    CORSMiddleware,
    # The Vite dev page: usually http://localhost:5173, or the next free port if that one is taken.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):51\d\d",
    allow_methods=["*"],
    allow_headers=["*"],
)

# One team run at a time: agents share one cash account and one MCP connection.
_run_lock = asyncio.Lock()
_runs: dict[str, dict] = {}

# Audit events the board cares about: what agents said, tools, delegations, decisions.
BOARD_EVENTS = {
    "ticket_start", "ticket_done", "agent_start", "agent_done", "model_response",
    "tool_call", "tool_result", "tool_blocked", "delegate", "delegate_result", "delegate_refused",
    "limit_hit", "agent_error", "human_tool_call", "human_tool_result", "database_reset",
}


class ApproveBody(BaseModel):
    approved_by: str


class RejectBody(BaseModel):
    decided_by: str
    note: str = ""


def _mcp_error(result) -> None:
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result)


# ------------------------------------------------------------------ tickets

@app.get("/api/tickets")
async def list_tickets():
    """All tickets with status, is_open and is_resolved."""
    return await human_call("list_tickets", {})


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    """One ticket with its log, drafts and approval requests."""
    result = await human_call("get_ticket", {"ticket_id": ticket_id})
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


async def _run_ticket(run_id: str, ticket_id: int) -> None:
    run = _runs[run_id]
    try:
        async with _run_lock:
            run["status"] = "running"
            decisions = await work_tickets([ticket_id], run_id=run_id)
            run.update(status="done", decision=decisions[0] if decisions else None)
    except Exception as exc:  # surface failures to the dashboard
        run.update(status="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        run["finished_at"] = datetime.now().isoformat(timespec="seconds")


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, wait: bool = False):
    """Run the agent team (Boss first) on one ticket.

    Returns immediately with a run_id; poll /api/runs/{run_id} and /api/events.
    Pass ?wait=true to block until the Boss's decision is ready.
    """
    ticket = await human_call("get_ticket", {"ticket_id": ticket_id})
    if isinstance(ticket, dict) and "error" in ticket:
        raise HTTPException(status_code=404, detail=ticket["error"])
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="The team is already working a ticket. Try again when it finishes.")

    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {
        "run_id": run_id, "ticket_id": ticket_id, "status": "queued",
        "model": MODEL_NAME, "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    task = asyncio.create_task(_run_ticket(run_id, ticket_id))
    if wait:
        await task
    return _runs[run_id]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Status of one team run (queued, running, done, error) and the Boss's decision."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Unknown run_id.")
    return _runs[run_id]


# ------------------------------------------------------------------ events

@app.get("/api/events")
async def recent_events(
    limit: int = Query(100, ge=1, le=1000),
    after: int = Query(-1, description="Only events with index greater than this (for incremental refresh)."),
    ticket_id: int | None = None,
    run_id: str | None = None,
):
    """Recent agent events from output/audit_trail.json: what each agent said and which tools it used."""
    trail = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8")) if AUDIT_TRAIL.exists() else []
    events = []
    for index, e in enumerate(trail):
        if index <= after or e.get("event") not in BOARD_EVENTS:
            continue
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and e.get("run_id") != run_id:
            continue
        events.append({"index": index, **e})
    return {
        "total": len(trail),
        "last_index": len(trail) - 1,
        "running": _run_lock.locked(),
        "events": events[-limit:],
    }


# ------------------------------------------------------------------ approvals (human only)

@app.get("/api/approvals")
async def list_approvals(status: str = "pending"):
    """Payment and purchase-order requests the agents prepared (pending, paid, rejected or all)."""
    return await human_call("list_approval_requests", {"status": status})


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, body: ApproveBody):
    """A human clicked Approve: pay the request. The only route that changes cash."""
    if not body.approved_by.strip():
        raise HTTPException(status_code=400, detail="approved_by (the human's name) is required.")
    result = await human_action("approve_and_pay", {"request_id": request_id, "approved_by": body.approved_by})
    _mcp_error(result)
    return result


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, body: RejectBody):
    """A human clicked Reject: no money moves."""
    result = await human_action(
        "reject_request", {"request_id": request_id, "decided_by": body.decided_by, "note": body.note})
    _mcp_error(result)
    return result


# ------------------------------------------------------------------ cash

@app.get("/api/cash")
async def cash():
    """Current checking balance from cash_accounts, plus what is pending approval."""
    position = await human_call("get_cash_position", {})
    checking = next((a for a in position["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(status_code=404, detail="No checking account in cash_accounts.")
    return {
        "account": "checking",
        "balance": checking["balance"],
        "as_of": checking["date"],
        "shop_today": position["shop_today"],
        "pending_total": position["pending_total"],
        "cash_after_pending": position["cash_after_pending"],
    }


# ------------------------------------------------------------------ reset

@app.post("/api/reset")
async def reset():
    """Copy data/campus_customs.db over data/campus_customs_new.db for a fresh run.

    The audit trail is kept (it is append-only); the reset itself is logged.
    """
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="Can't reset while the team is working a ticket.")
    reset_db()
    await audit.record(TeamDeps(run_id="human-reset", ticket_id=None, agent="human"), "database_reset",
                       "campus_customs.db -> campus_customs_new.db")
    return {"reset": True, "database": "data/campus_customs_new.db", "from": "data/campus_customs.db"}


@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL_NAME, "running": _run_lock.locked()}
