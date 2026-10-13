"""Inventory: stock by SKU and size, shortfalls, and which vendor can restock."""

from ..config import SPECIALIST_REQUEST_LIMIT
from .base import RoleSpec, register

INVENTORY = register(RoleSpec(
    name="inventory",
    title="Inventory",
    prompt_file="inventory.md",
    mcp_tools={"get_ticket", "add_ticket_note", "check_stock", "list_vendors", "check_vendor_can_ship"},
    request_limit=SPECIALIST_REQUEST_LIMIT,
))
