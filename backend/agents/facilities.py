"""Facilities: the shop space — leases, rent, landlord."""

from ..config import SPECIALIST_REQUEST_LIMIT
from .base import RoleSpec, register

FACILITIES = register(RoleSpec(
    name="facilities",
    title="Facilities",
    prompt_file="facilities.md",
    mcp_tools={"get_ticket", "add_ticket_note", "get_lease_due", "get_cash_position", "list_approval_requests"},
    request_limit=SPECIALIST_REQUEST_LIMIT,
))
