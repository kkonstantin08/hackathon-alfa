"""Трасса: каждый шаг агента и каждый вызов модели → TraceEvent в SQLite. Идея — event bus из CrewAI, без pub/sub."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from app import store
from contracts.models import TraceEvent

_current: ContextVar[str | None] = ContextVar("trace_id", default=None)


def new_trace(prefix: str = "t") -> str:
    tid = f"{prefix}_{uuid.uuid4().hex[:12]}"
    _current.set(tid)
    return tid


def current() -> str:
    return _current.get() or new_trace()


def emit(step: str, **kw) -> TraceEvent:
    ev = TraceEvent(trace_id=current(), step=step, ts=datetime.now(UTC), **kw)
    with store.conn() as c:
        c.execute(
            "INSERT INTO traces(trace_id, ts, step, body) VALUES (?, ?, ?, ?)",
            (ev.trace_id, ev.ts.isoformat(), step, ev.model_dump_json()),
        )
    return ev


def get(trace_id: str) -> list[TraceEvent]:
    rows = store.raw("SELECT body FROM traces WHERE trace_id = ? ORDER BY ts", (trace_id,))
    return [TraceEvent.model_validate_json(r[0]) for r in rows]
