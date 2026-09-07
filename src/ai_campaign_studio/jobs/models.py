"""Job state model (P0.20).

Owns the ``JobStatus`` lifecycle enum and the immutable ``JobState`` snapshot
returned by ``JobManager.get_state``. Does not run jobs, emit events or manage
concurrency — those live in ``manager.py``/``events.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

    ACS-F1-047 added ``generated_count`` / ``failed_count`` /
    ``content_piece_ids`` so the ``generate_campaign_content`` job
    can expose its per-piece outcomes to JS via ``get_job_status``
    without a second round-trip. All three are aditive (defaulted),
    so pre-F1-047 tests / call-sites that construct ``JobState``
    positionally (id, job_type, status) keep working unchanged.
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
    # ACS-F1-047: per-piece outcome for ``generate_campaign_content``.
    # ``generated_count`` + ``failed_count`` always equal
    # ``progress_current`` (modulo cooperative cancellation which may
    # freeze progress at < total). ``content_piece_ids`` is the tuple
    # of DB ids of the pieces that actually landed.
    generated_count: int = 0
    failed_count: int = 0
    content_piece_ids: tuple[str, ...] = field(default_factory=tuple)
