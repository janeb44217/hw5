"""Shared machinery for the five agents: role specs, the delegation tool, and
the audited agent loop.

Full connectivity: every agent has the same ask_agent tool and may hand a task
to any other agent (never itself). Delegation depth and the number of
delegations per ticket are capped so agents cannot ping-pong forever.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from .. import audit
from ..config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    TOTAL_TOKENS_PER_AGENT_RUN,
    build_model,
    load_prompt,
)
from ..mcp_link import toolset_for
from ..models import TeamDeps

AGENT_ROLES = ("boss", "inventory", "accounting", "facilities", "customer_service")


@dataclass
class RoleSpec:
    name: str
    title: str
    prompt_file: str
    mcp_tools: set[str]
    request_limit: int
    output_type: Any = str
    can_delegate_to: tuple[str, ...] = field(default=AGENT_ROLES)


_REGISTRY: dict[str, RoleSpec] = {}
_AGENTS: dict[str, Agent] = {}


def register(spec: RoleSpec) -> RoleSpec:
    _REGISTRY[spec.name] = spec
    return spec


async def ask_agent(
    ctx: RunContext[TeamDeps],
    agent: Literal["boss", "inventory", "accounting", "facilities", "customer_service"],
    request: str,
) -> str:
    """Hand a task to another agent on the team and get its written answer back.

    Write a self-contained request: include the ticket id and every fact the
    other agent needs (SKU, size, qty, vendor id, invoice id, lease id, amounts).
    """
    deps = ctx.deps
    budget = deps.budget
    refusal = None
    if agent == deps.agent:
        refusal = "You cannot delegate to yourself. Do the work with your own tools."
    elif agent not in _REGISTRY:
        refusal = f"Unknown agent {agent!r}."
    elif deps.depth >= MAX_DELEGATION_DEPTH:
        refusal = (f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached. "
                   "Answer with what you have, or say what is missing.")
    elif budget.delegations >= MAX_DELEGATIONS_PER_TICKET:
        refusal = (f"This ticket already used {MAX_DELEGATIONS_PER_TICKET} delegations. "
                   "Finish with what the team has found so far.")
    if refusal:
        await audit.record(deps, "delegate_refused", f"{deps.agent} -> {agent}", {"request": request, "reason": refusal})
        return refusal

    budget.delegations += 1
    budget.chain.append(f"{deps.agent}->{agent}")
    child = deps.child(agent)
    await audit.record(deps, "delegate", f"{deps.agent} -> {agent}",
                       {"request": request, "delegation_no": budget.delegations})
    answer = await run_agent(agent, request, child)
    await audit.record(deps, "delegate_result", f"{agent} -> {deps.agent}", {"answer": str(answer)})
    return str(answer)


def get_agent(name: str) -> Agent:
    if name not in _AGENTS:
        spec = _REGISTRY[name]
        _AGENTS[name] = Agent(
            build_model(),
            name=spec.name,
            instructions=load_prompt(spec.prompt_file),
            deps_type=TeamDeps,
            output_type=spec.output_type,
            toolsets=[toolset_for(spec.mcp_tools)],
            tools=[ask_agent],
            retries=2,
        )
    return _AGENTS[name]


def _summarize_response(node) -> dict:
    texts, calls = [], []
    for part in node.model_response.parts:
        kind = getattr(part, "part_kind", "")
        if kind == "text" and part.content.strip():
            texts.append(part.content)
        elif kind == "tool-call":
            calls.append({"tool": part.tool_name, "args": part.args_as_dict()})
    usage = node.model_response.usage
    return {
        "text": "\n".join(texts),
        "tool_calls": calls,
        "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
    }


async def run_agent(name: str, prompt: str, deps: TeamDeps):
    """Run one agent's loop to completion, auditing every step."""
    spec = _REGISTRY[name]
    agent = get_agent(name)
    limits = UsageLimits(request_limit=spec.request_limit, total_tokens_limit=TOTAL_TOKENS_PER_AGENT_RUN)
    step = 0
    await audit.record(deps, "agent_start", spec.title, {"prompt": prompt})
    try:
        async with agent.iter(prompt, deps=deps, usage_limits=limits) as run:
            async for node in run:
                step += 1
                if Agent.is_user_prompt_node(node):
                    await audit.record(deps, "user_prompt", f"step {step}", {"prompt": prompt})
                elif Agent.is_model_request_node(node):
                    await audit.record(deps, "model_request", f"step {step}",
                                       {"parts": [p.part_kind for p in node.request.parts]})
                elif Agent.is_call_tools_node(node):
                    await audit.record(deps, "model_response", f"step {step}", _summarize_response(node))
        output = run.result.output
        usage = run.usage
        await audit.record(deps, "agent_done", spec.title, {
            "output": output.model_dump() if hasattr(output, "model_dump") else output,
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        })
        return output
    except UsageLimitExceeded as exc:
        await audit.record(deps, "limit_hit", spec.title, {"error": str(exc), "steps": step})
        return f"{spec.title} stopped: usage limit reached ({exc}). Partial work is in the ticket log."
    except Exception as exc:
        await audit.record(deps, "agent_error", spec.title, {"error": f"{type(exc).__name__}: {exc}", "steps": step})
        if deps.depth == 0:
            raise
        return f"{spec.title} hit an error: {exc}"
