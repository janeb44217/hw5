"""Customer Service: drafts every outgoing message. Drafts only — nothing is sent."""

from ..config import SPECIALIST_REQUEST_LIMIT
from .base import RoleSpec, register

CUSTOMER_SERVICE = register(RoleSpec(
    name="customer_service",
    title="Customer Service",
    prompt_file="customer_service.md",
    mcp_tools={"get_ticket", "add_ticket_note", "check_stock", "draft_message"},
    request_limit=SPECIALIST_REQUEST_LIMIT,
))
