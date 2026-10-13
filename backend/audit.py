"""Append-only audit trail at output/audit_trail.json.

The file is one JSON array. Each write loads the array, appends, and writes it
back atomically, so earlier runs are never wiped.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any

from .config import AUDIT_TEXT_LIMIT, AUDIT_TRAIL, MODEL_NAME
from .models import AuditEvent, TeamDeps

_lock = asyncio.Lock()


def _clip(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= AUDIT_TEXT_LIMIT else value[:AUDIT_TEXT_LIMIT] + "…[truncated]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clip(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clip(str(value))


def _read() -> list:
    if not AUDIT_TRAIL.exists():
        return []
    try:
        data = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        # Never destroy evidence: keep the unreadable file and start a new array.
        AUDIT_TRAIL.rename(AUDIT_TRAIL.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json"))
        return []
    return data if isinstance(data, list) else [data]


async def record(deps: TeamDeps, event: str, detail: str = "", data: Any = None) -> None:
    entry = AuditEvent(
        ts=datetime.now().isoformat(timespec="milliseconds"),
        run_id=deps.run_id,
        ticket_id=deps.ticket_id,
        agent=deps.agent,
        depth=deps.depth,
        event=event,
        detail=_clip(detail),
        data=_clip(data),
        model=MODEL_NAME,
    )
    async with _lock:
        AUDIT_TRAIL.parent.mkdir(parents=True, exist_ok=True)
        trail = _read()
        trail.append(entry.model_dump())
        tmp = AUDIT_TRAIL.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(trail, indent=2), encoding="utf-8")
        os.replace(tmp, AUDIT_TRAIL)
