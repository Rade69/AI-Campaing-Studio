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
from concurrent.futures import Future, ThreadPoolExecutor
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
        self._futures: dict[str, Future[None]] = {}
        self._callbacks: list[JobCallback] = []
        # ``RLock`` (not ``Lock``) is required so that ``submit()`` can
        # call ``self._emit()`` from inside the same thread that holds
        # the lock — ``_emit`` itself takes the lock to snapshot
        # ``self._callbacks``. A non-reentrant ``Lock`` would deadlock
        # here. The reentrant property is thread-local: the worker
        # thread (``_run``) still has to wait for the submitter to
        # release the lock before it can transition the state to
        # ``RUNNING``, so the ``CREATED`` event is guaranteed to reach
        # subscribers before ``STARTED`` for the same job.
        self._lock = threading.RLock()
        self._shutdown = False

    def submit(self, job_type: str, func: Callable[..., Any]) -> str:
        """Schedule ``func`` and return its job id.

        ``func`` is called with no arguments unless it declares a ``token``
        parameter (or ``**kwargs``), in which case the job's
        ``CancellationToken`` is passed as the ``token`` keyword argument so it
        can cooperate with ``cancel`` via ``token.raise_if_cancelled()``.

        ACS-F1-047: ``CancellationToken`` carries its own ``job_id`` (set
        HERE, before the future is registered). This is the deterministic
        channel by which the worker closure learns its own job id --
        looking it up from ``_jobs`` would be ambiguous whenever two or
        more jobs of any type are concurrently RUNNING on the shared
        ``JobManager`` executor.

        Raises ``RuntimeError`` if the manager has been shut down. In that case
        no ``CREATED`` event is emitted and no job state is recorded.

        Ordering invariant: the ``CREATED`` event is published **inside**
        the ``with self._lock:`` block (after the future is successfully
        registered), so any worker thread waiting on the lock to perform
        its PENDING → RUNNING transition cannot run until the submitter
        has finished emitting ``CREATED``. Subscribers therefore always
        observe ``CREATED`` before ``STARTED`` for the same job.
        """
        job_id = new_id()
        # Populate the token's ``job_id`` BEFORE registering the future so
        # the worker can read ``token.job_id`` from the moment the
        # closure starts on its executor thread. No race: the value is
        # written by this thread and read by exactly one worker.
        token = CancellationToken(job_id=job_id)
        state = JobState(id=job_id, job_type=job_type, status=JobStatus.PENDING)
        with self._lock:
            if self._shutdown:
                raise RuntimeError(
                    "cannot submit new jobs: JobManager is shut down"
                )
            self._jobs[job_id] = state
            self._tokens[job_id] = token
            try:
                future = self._executor.submit(self._run, job_id, func, token)
            except RuntimeError:
                # Roll back so no orphan PENDING job or CREATED event leaks.
                self._jobs.pop(job_id, None)
                self._tokens.pop(job_id, None)
                raise
            self._futures[job_id] = future
            # Publish ``CREATED`` while still holding the lock so the
            # worker thread cannot race ahead and emit ``STARTED`` first.
            # ``_emit`` acquires the (reentrant) lock internally to
            # snapshot ``self._callbacks``; the same-thread re-acquire
            # is safe with ``RLock``.
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

    def update_progress(
        self,
        job_id: str,
        current: int,
        total: int,
        phase: str = "",
        message: str = "",
    ) -> None:
        """Update progress fields on a RUNNING job.

        Best-effort: silently no-ops on unknown / terminal / non-RUNNING
        jobs so a progress update that loses a race with the worker's
        ``_finish()`` (or with cancellation) can never raise into user
        code. The whole point of progress is "fires often, never blocks";
        callers should not need to wrap each call in a try/except.

        Emits a ``PROGRESS`` event on the same lock-hold pattern as the
        lifecycle events (``_emit`` takes ``self._lock`` internally), so
        subscribers observe ``STARTED`` before any ``PROGRESS`` and
        progress stops after a terminal transition (the job is no longer
        RUNNING, so the no-op short-circuits).

        Added in ACS-F1-047 (generate_campaign_content JobManager
        wiring). No prior job type in the codebase published progress
        so this is the first non-lifecycle event the manager emits.
        """
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                return
            # Terminal jobs do not accept progress updates; this also
            # covers ``CANCELLING`` (the worker is about to land in
            # ``CANCELLED`` and we don't want a stale progress event to
            # race the terminal one).
            if state.status is not JobStatus.RUNNING:
                return
            self._jobs[job_id] = replace(
                state,
                progress_current=current,
                progress_total=total,
                phase=phase,
                message=message,
            )
        # Emit OUTSIDE the lock-content section above but still under
        # the same ``_emit``-takes-lock pattern as lifecycle events,
        # so the ordering invariant (STARTED before any PROGRESS for
        # the same job) holds against any concurrent worker.
        self._emit(
            JobEvent(
                job_id=job_id,
                event_type=JobEventType.PROGRESS,
                timestamp=utc_now(),
                payload={
                    "current": current,
                    "total": total,
                    "phase": phase,
                    "message": message,
                },
            )
        )

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
        self._finish_cancelled_futures()

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

    def _finish_cancelled_futures(self) -> None:
        """Mark executor-cancelled queued jobs as terminally cancelled."""
        cancelled_events: list[JobEvent] = []
        with self._lock:
            for job_id, future in self._futures.items():
                if not future.cancelled():
                    continue
                state = self._jobs.get(job_id)
                if state is None or state.status in _TERMINAL_STATUSES:
                    continue
                self._jobs[job_id] = replace(
                    state, status=JobStatus.CANCELLED, finished_at=utc_now()
                )
                cancelled_events.append(
                    JobEvent(
                        job_id=job_id,
                        event_type=JobEventType.CANCELLED,
                        timestamp=utc_now(),
                    )
                )
        for event in cancelled_events:
            self._emit(event)

    def _emit(self, event: JobEvent) -> None:
        # Hold ``self._lock`` across the entire callback dispatch, not
        # just the callback-snapshot step. The reason is the event
        # ordering invariant: a ``CREATED`` event must reach subscribers
        # before any worker thread can perform the PENDING → RUNNING
        # transition and emit ``STARTED``. The worker thread needs
        # ``self._lock`` for that transition; if the lock were released
        # between snapshot and callback execution, a slow CREATED
        # subscriber would let the worker race ahead and emit
        # ``STARTED`` first (regression observed on Linux CI; see
        # ACS-HOTFIX-001 task contract).
        #
        # Trade-off: callbacks now run with the lock held, so a slow
        # subscriber briefly serialises other manager operations
        # (cancel, get_state, submit, _run, _finish). This is the
        # correct trade-off for the ordering invariant; the lock
        # reentrancy (``RLock``) keeps ``_emit``-from-inside-itself
        # cases (currently none) safe.
        with self._lock:
            callbacks = list(self._callbacks)
            for callback in callbacks:
                try:
                    callback(event)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "job event callback failed for %s",
                        event.event_type.value,
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
