"""Boss: reads each ticket, routes the work, and makes the final call."""

from ..config import BOSS_REQUEST_LIMIT
from ..models import TicketDecision
from .base import RoleSpec, register

BOSS = register(RoleSpec(
    name="boss",
    title="Boss",
    prompt_file="boss.md",
    mcp_tools={
        "list_open_tickets", "get_ticket", "add_ticket_note", "set_ticket_status",
        "get_cash_position", "list_approval_requests",
    },
    request_limit=BOSS_REQUEST_LIMIT,
    output_type=TicketDecision,
))
