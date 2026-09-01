"""Thread-based job manager (P0.20).

Owns scheduling callables on a ``ThreadPoolExecutor``, tracking their
``JobState``, publishing ``JobEvent`` objects to subscribers, and cooperative
cancellation. Does not provide a process pool, Playwright subprocess or AI
retry logic — those arrive in later phases.
"""

from __future__ import annotations

import inspect
import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

from ai_campaign_studio.domain.common.errors import AppError, JobError
from ai_campaign_studio.domain.common.ids import new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.jobs.cancellation import CancellationError, CancellationToken
from ai_campaign_studio.jobs.events import JobEvent, JobEventType
from ai_campaign_studio.jobs.models import JobState, JobStatus

logger = logging.getLogger("ai_campaign_studio.jobs.manager")

JobCallback = Callable[[JobEvent], None]

_TERMINAL_STATUSES = frozenset(
    {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
)


class JobManager:
    """Framework-neutral background job manager over ``ThreadPoolExecutor``."""

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, JobState] = {}
        self._tokens: dict[str, CancellationToken] = {}
        self._callbacks: list[JobCallback] = []
        self._lock = threading.Lock()
        self._shutdown = False

    def submit(self, job_type: str, func: Callable[..., Any]) -> str:
        """Schedule ``func`` and return its job id.

        ``func`` is called with no arguments unless it declares a ``token``
        parameter (or ``**kwargs``), in which case the job's
        ``CancellationToken`` is passed as the ``token`` keyword argument so it
        can cooperate with ``cancel`` via ``token.raise_if_cancelled()``.

        Raises ``RuntimeError`` if the manager has been shut down. In that case
        no ``CREATED`` event is emitted and no job state is recorded.
        """
        job_id = new_id()
        token = CancellationToken()
        state = JobState(id=job_id, job_type=job_type, status=JobStatus.PENDING)
        with self._lock:
            if self._shutdown:
                raise RuntimeError(
                    "cannot submit new jobs: JobManager is shut down"
                )
            self._jobs[job_id] = state
            self._tokens[job_id] = token
            try:
                self._executor.submit(self._run, job_id, func, token)
            except RuntimeError:
                # Roll back so no orphan PENDING job or CREATED event leaks.
                self._jobs.pop(job_id, None)
                self._tokens.pop(job_id, None)
                raise
        self._emit(
            JobEvent(
                job_id=job_id,
                event_type=JobEventType.CREATED,
                timestamp=utc_now(),
            )
        )
        return job_id

    def get_state(self, job_id: str) -> JobState:
        """Return the current immutable ``JobState`` snapshot."""
        with self._lock:
            state = self._jobs.get(job_id)
        if state is None:
            raise JobError(f"unknown job: {job_id}")
        return state

    def cancel(self, job_id: str) -> None:
        """Cooperatively cancel a job.

        A ``PENDING`` job transitions straight to ``CANCELLED``. A ``RUNNING``
        job transitions to ``CANCELLING`` and the running callable is expected
        to stop at its next ``token.raise_if_cancelled()`` check. Jobs already
        in a terminal state are left untouched.
        """
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                raise JobError(f"unknown job: {job_id}")
            if (
                state.status in _TERMINAL_STATUSES
                or state.status is JobStatus.CANCELLING
            ):
                return
            if state.status is JobStatus.PENDING:
                self._jobs[job_id] = replace(
                    state, status=JobStatus.CANCELLED, finished_at=utc_now()
                )
                emit_cancelled = True
                emit_cancel_requested = False
            else:  # RUNNING
                self._jobs[job_id] = replace(state, status=JobStatus.CANCELLING)
                emit_cancelled = False
                emit_cancel_requested = True

        if emit_cancel_requested:
            # Emit before request_cancel so CANCELLATION_REQUESTED is observed
            # before the worker can observe the token and emit CANCELLED.
            self._emit(
                JobEvent(
                    job_id=job_id,
                    event_type=JobEventType.CANCELLATION_REQUESTED,
                    timestamp=utc_now(),
                )
            )
            self._tokens[job_id].request_cancel()
        elif emit_cancelled:
            self._emit(
                JobEvent(
                    job_id=job_id,
                    event_type=JobEventType.CANCELLED,
                    timestamp=utc_now(),
                )
            )

    def subscribe(self, callback: JobCallback) -> Callable[[], None]:
        """Register an event callback; return an unsubscribe callable."""
        with self._lock:
            self._callbacks.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return unsubscribe

    def shutdown(self, wait: bool = True) -> None:
        """Stop accepting work; wait for running jobs when ``wait`` is True.

        Idempotent. After shutdown, ``submit`` raises ``RuntimeError`` without
        emitting ``CREATED`` or recording job state.
        """
        with self._lock:
            self._shutdown = True
        self._executor.shutdown(wait=wait, cancel_futures=True)

    # --- internals ---

    def _run(
        self, job_id: str, func: Callable[..., Any], token: CancellationToken
    ) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None or state.status is JobStatus.CANCELLED:
                # Cancelled before the worker reached the RUNNING transition.
                return
            self._jobs[job_id] = replace(
                state, status=JobStatus.RUNNING, started_at=utc_now()
            )
        self._emit(
            JobEvent(
                job_id=job_id,
                event_type=JobEventType.STARTED,
                timestamp=utc_now(),
            )
        )
        try:
            if _accepts_token(func):
                func(token=token)
            else:
                func()
        except CancellationError:
            self._finish(job_id, JobStatus.CANCELLED, JobEventType.CANCELLED)
        except Exception as exc:  # noqa: BLE001
            self._finish(job_id, JobStatus.FAILED, JobEventType.FAILED, error=exc)
        else:
            self._finish(job_id, JobStatus.SUCCEEDED, JobEventType.SUCCEEDED)

    def _finish(
        self,
        job_id: str,
        status: JobStatus,
        event_type: JobEventType,
        error: Exception | None = None,
    ) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None or state.status in _TERMINAL_STATUSES:
                return
            if error is not None:
                updated = replace(
                    state,
                    status=status,
                    finished_at=utc_now(),
                    error_code=_error_code(error),
                    error_message=str(error),
                )
            else:
                updated = replace(state, status=status, finished_at=utc_now())
            self._jobs[job_id] = updated
        self._emit(
            JobEvent(job_id=job_id, event_type=event_type, timestamp=utc_now())
        )

    def _emit(self, event: JobEvent) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            try:
                callback(event)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "job event callback failed for %s", event.event_type.value
                )


def _accepts_token(func: Callable[..., Any]) -> bool:
    """Return True if ``func`` can receive ``token`` as a keyword argument."""
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == "token" and parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            return True
    return False


def _error_code(error: BaseException) -> str:
    if isinstance(error, AppError):
        return str(error.error_code)
    return type(error).__name__
