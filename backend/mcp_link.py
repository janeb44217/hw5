"""The agents' only path to shop data: the campus-customs MCP server.

One stdio MCP connection is shared by the whole team. Each agent sees a
filtered view with just its own tools. Every tool call goes through
_process_tool_call, which
  1. stamps the caller's real name on identity fields (an agent cannot pose as
     the Boss or as another agent), and
  2. writes the call and its result to the audit trail.

The human approval path (approve_and_pay / reject_request) is never given to an
agent. The runner and the dashboard call it through human_call().
"""

from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import MCPToolset

from . import audit
from .config import PROJECT, mcp_command
from .models import TeamDeps

HUMAN_ONLY_TOOLS = {"approve_and_pay", "reject_request"}

# Tool argument that must always equal the calling agent's own name.
IDENTITY_ARG = {
    "add_ticket_note": "author",
    "set_ticket_status": "author",
    "draft_message": "author",
    "request_payment": "requested_by",
    "request_purchase_order": "requested_by",
}


def _transport() -> StdioTransport:
    command, args = mcp_command()
    return StdioTransport(command=command, args=args, cwd=str(PROJECT))


async def _process_tool_call(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict[str, Any]):
    deps = ctx.deps
    if name in HUMAN_ONLY_TOOLS:  # belt and braces: filtered out already
        result = {"error": f"{name} is human-only. Agents cannot approve or pay."}
        await audit.record(deps, "tool_blocked", name, {"args": args, "result": result})
        return result
    if name in IDENTITY_ARG:
        args = {**args, IDENTITY_ARG[name]: deps.agent}

    await audit.record(deps, "tool_call", name, {"args": args})
    try:
        result = await call_tool(name, args)
    except Exception as exc:
        await audit.record(deps, "tool_error", name, {"args": args, "error": str(exc)})
        raise
    await audit.record(deps, "tool_result", name, {"result": result})
    return result


shop_mcp = MCPToolset(
    Client(_transport()),
    id="campus-customs",
    process_tool_call=_process_tool_call,
)


def toolset_for(tool_names: set[str]):
    """A view of the MCP server that exposes only this agent's tools."""
    allowed = set(tool_names) - HUMAN_ONLY_TOOLS
    return shop_mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed)


async def human_call(tool: str, args: dict[str, Any]) -> Any:
    """Call an MCP tool as the human operator (approvals, rejections, reads)."""
    async with Client(_transport()) as client:
        result = await client.call_tool(tool, args, raise_on_error=False)
    if result.structured_content is not None:
        return result.structured_content
    return "\n".join(getattr(c, "text", "") for c in result.content)
