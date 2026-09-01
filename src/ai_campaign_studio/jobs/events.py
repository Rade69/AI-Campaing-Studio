"""Job event model (P0.20).

Owns the ``JobEventType`` enum and the immutable ``JobEvent`` published to
``JobManager.subscribe`` callbacks. ``PROGRESS``/``PHASE_CHANGED`` are
declared now for the future progress-reporting surface; the P0 manager only
emits lifecycle events (see ``manager.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class JobEventType(StrEnum):
    """Kinds of events a job can publish."""

    CREATED = "CREATED"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    PHASE_CHANGED = "PHASE_CHANGED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class JobEvent:
    """A single immutable job event delivered to subscribers."""

    job_id: str
    event_type: JobEventType
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)
