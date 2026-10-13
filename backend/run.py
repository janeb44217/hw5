"""Command-line runner for the Campus Customs agent team.

  python -m backend.run reset                      # copy campus_customs.db -> campus_customs_new.db
  python -m backend.run work 101                   # Boss works one ticket (delegating as needed)
  python -m backend.run work --all                 # Boss works every open ticket in order
  python -m backend.run approvals                  # list requests waiting on a human
  python -m backend.run approve 1 --by "Jane Bary" # HUMAN approves + pays request 1
  python -m backend.run reject 2 --by "Jane Bary" --note "not now"

Every agent step is appended to output/audit_trail.json.
"""

import argparse
import asyncio
import json
import shutil
import uuid

from . import audit
from .agents import run_agent
from .config import ORIGINAL_DB, WORKING_DB
from .mcp_link import human_call, shop_mcp
from .models import TeamDeps


def reset_db() -> None:
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database missing: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}.")


async def work_tickets(ticket_ids: list[int] | None, run_id: str | None = None) -> list[dict]:
    run_id = run_id or uuid.uuid4().hex[:12]
    decisions = []
    async with shop_mcp:  # one MCP connection for the whole team
        if ticket_ids is None:
            board = await human_call("list_open_tickets", {})
            ticket_ids = [t["id"] for t in board["tickets"]]
        for ticket_id in ticket_ids:
            deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss")
            await audit.record(deps, "ticket_start", f"ticket {ticket_id}")
            decision = await run_agent("boss", f"Work ticket #{ticket_id}.", deps)
            data = decision.model_dump() if hasattr(decision, "model_dump") else {"output": str(decision)}
            data["delegation_chain"] = deps.budget.chain
            await audit.record(deps, "ticket_done", f"ticket {ticket_id}", data)
            decisions.append(data)
            print(json.dumps(data, indent=2))
    return decisions


async def human_action(tool: str, args: dict) -> dict:
    deps = TeamDeps(run_id="human-" + uuid.uuid4().hex[:8], ticket_id=None, agent="human")
    await audit.record(deps, "human_tool_call", tool, {"args": args})
    result = await human_call(tool, args)
    await audit.record(deps, "human_tool_result", tool, {"result": result})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reset")
    w = sub.add_parser("work")
    w.add_argument("ticket_ids", nargs="*", type=int)
    w.add_argument("--all", action="store_true")
    sub.add_parser("approvals")
    a = sub.add_parser("approve")
    a.add_argument("request_id", type=int)
    a.add_argument("--by", required=True, help="Name of the human approving")
    r = sub.add_parser("reject")
    r.add_argument("request_id", type=int)
    r.add_argument("--by", required=True)
    r.add_argument("--note", default="")
    args = parser.parse_args()

    if args.cmd == "reset":
        reset_db()
    elif args.cmd == "work":
        if not args.all and not args.ticket_ids:
            parser.error("give ticket ids or --all")
        asyncio.run(work_tickets(None if args.all else args.ticket_ids))
    elif args.cmd == "approvals":
        print(json.dumps(asyncio.run(human_call("list_approval_requests", {"status": "pending"})), indent=2))
    elif args.cmd == "approve":
        result = asyncio.run(human_action("approve_and_pay", {"request_id": args.request_id, "approved_by": args.by}))
        print(json.dumps(result, indent=2))
    elif args.cmd == "reject":
        result = asyncio.run(human_action(
            "reject_request", {"request_id": args.request_id, "decided_by": args.by, "note": args.note}))
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
