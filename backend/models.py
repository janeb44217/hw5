"""Data types shared by the agents, the runner, and (later) the FastAPI app."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved", "declined"]


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    final_status: TicketStatus = Field(description="Status the Boss set on the ticket.")
    decision: str = Field(description="One or two sentences: what the shop will do and why.")
    facts_used: list[str] = Field(
        default_factory=list,
        description="Database facts the decision rests on, each quoted from a tool result.",
    )
    pending_approval_ids: list[int] = Field(
        default_factory=list, description="approval_requests ids waiting on a human."
    )
    draft_ids: list[int] = Field(default_factory=list, description="drafts ids saved for this ticket.")
    blocked_by: list[str] = Field(
        default_factory=list, description="What must happen before the ticket can close."
    )
    next_step_for_human: str = Field(description="Exactly what the human should do next, or 'nothing'.")


class AuditEvent(BaseModel):
    """One line in output/audit_trail.json."""

    ts: str
    run_id: str
    ticket_id: int | None
    agent: str
    depth: int
    event: str
    detail: str = ""
    data: Any = None
    model: str | None = None


@dataclass
class RunBudget:
    """Shared across every agent working one ticket, so limits are per ticket."""

    delegations: int = 0
    chain: list[str] = field(default_factory=list)


@dataclass
class TeamDeps:
    """Per-agent-run context. A delegated agent gets a copy with its own name and depth."""

    run_id: str
    ticket_id: int | None
    agent: str
    depth: int = 0
    budget: RunBudget = field(default_factory=RunBudget)

    def child(self, agent: str) -> "TeamDeps":
        return TeamDeps(self.run_id, self.ticket_id, agent, self.depth + 1, self.budget)
