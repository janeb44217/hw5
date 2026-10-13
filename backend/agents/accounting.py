"""Accounting: cash, invoices, margins, and payment / PO requests for human approval."""

from ..config import SPECIALIST_REQUEST_LIMIT
from .base import RoleSpec, register

ACCOUNTING = register(RoleSpec(
    name="accounting",
    title="Accounting",
    prompt_file="accounting.md",
    mcp_tools={
        "get_ticket", "add_ticket_note", "get_cash_position", "get_invoice", "check_margin",
        "check_vendor_can_ship", "get_lease_due", "request_payment", "request_purchase_order",
        "list_approval_requests",
    },
    request_limit=SPECIALIST_REQUEST_LIMIT,
))
