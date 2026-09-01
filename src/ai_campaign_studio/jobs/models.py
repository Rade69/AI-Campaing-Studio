"""Job state model (P0.20).

Owns the ``JobStatus`` lifecycle enum and the immutable ``JobState`` snapshot
returned by ``JobManager.get_state``. Does not run jobs, emit events or manage
concurrency — those live in ``manager.py``/``events.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle states of a background job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class JobState:
    """Immutable snapshot of a job's observable state.

    The manager replaces the whole snapshot on every transition (via
    ``dataclasses.replace``) so readers always see a consistent, thread-safe
    view; there is no in-place mutation.
    """

    id: str
    job_type: str
    status: JobStatus
    progress_current: int = 0
    progress_total: int = 0
    phase: str = ""
    message: str = ""
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
