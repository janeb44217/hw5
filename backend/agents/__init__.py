"""The Campus Customs agent team. Importing this package registers all five roles."""

from . import accounting, boss, customer_service, facilities, inventory  # noqa: F401
from .base import AGENT_ROLES, run_agent

__all__ = ["AGENT_ROLES", "run_agent"]
