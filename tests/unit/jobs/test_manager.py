"""Unit tests for JobManager (P0.20)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest

from ai_campaign_studio.domain.common.errors import JobError
from ai_campaign_studio.jobs.events import JobEvent, JobEventType
from ai_campaign_studio.jobs.manager import JobManager
from ai_campaign_studio.jobs.models import JobState, JobStatus

_WAIT_TIMEOUT = 5.0


def _wait_for_status(
    manager: JobManager,
    job_id: str,
    statuses: set[JobStatus],
    timeout: float = _WAIT_TIMEOUT,
) -> JobState:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = manager.get_state(job_id)
        if state.status in statuses:
            return state
        time.sleep(0.005)
    raise AssertionError(
        f"job {job_id} did not reach {statuses}; "
        f"last state={manager.get_state(job_id)}"
    )


def _collect_events(
    manager: JobManager,
) -> tuple[list[JobEventType], Callable[[], None]]:
    events: list[JobEventType] = []
    lock = threading.Lock()

    def callback(event: JobEvent) -> None:
        with lock:
            events.append(event.event_type)

    unsubscribe = manager.subscribe(callback)
    return events, unsubscribe


def _slow_work() -> None:
    time.sleep(0.1)


def _failing_work() -> None:
    raise ValueError("boom")


def _cooperative_work(token) -> None:  # type: ignore[no-untyped-def]
    while True:
        token.raise_if_cancelled()
        time.sleep(0.005)


def _cooperative_bounded(token) -> None:  # type: ignore[no-untyped-def]
    # Performs "real work" in steps and checks the token each step.
    for _ in range(2000):
        token.raise_if_cancelled()
        time.sleep(0.001)


def test_happy_path_pending_running_succeeded() -> None:
    manager = JobManager()
    try:
        job_id = manager.submit("work", _slow_work)
        final = _wait_for_status(manager, job_id, {JobStatus.SUCCEEDED})
        assert final.error_code is None
        assert final.error_message is None
        assert final.started_at is not None
        assert final.finished_at is not None
    finally:
        manager.shutdown()


def test_failure_sets_typed_error_info() -> None:
    manager = JobManager()
    try:
        job_id = manager.submit("work", _failing_work)
        final = _wait_for_status(manager, job_id, {JobStatus.FAILED})
        assert final.error_code == "ValueError"
        assert final.error_message == "boom"
    finally:
        manager.shutdown()


def test_cooperative_cancellation_stops_work() -> None:
    manager = JobManager()
    total_steps = 5000
    steps_done = 0

    def work(token) -> None:  # type: ignore[no-untyped-def]
        nonlocal steps_done
        for _ in range(total_steps):
            token.raise_if_cancelled()
            steps_done += 1
            time.sleep(0.001)

    try:
        job_id = manager.submit("work", work)
        _wait_for_status(manager, job_id, {JobStatus.RUNNING})
        manager.cancel(job_id)
        final = _wait_for_status(manager, job_id, {JobStatus.CANCELLED})
        assert final.status is JobStatus.CANCELLED
        assert final.error_code is None
        # Work actually stopped: not all steps completed.
        assert steps_done < total_steps
    finally:
        manager.shutdown()


def test_cancel_pending_job_transitions_to_cancelled() -> None:
    manager = JobManager(max_workers=1)
    blocker_started = threading.Event()
    release_blocker = threading.Event()

    def blocker() -> None:
        blocker_started.set()
        release_blocker.wait(_WAIT_TIMEOUT)

    try:
        manager.submit("blocker", blocker)
        assert blocker_started.wait(_WAIT_TIMEOUT)

        job_id = manager.submit("work", _slow_work)
        assert manager.get_state(job_id).status is JobStatus.PENDING
        manager.cancel(job_id)
        final = _wait_for_status(manager, job_id, {JobStatus.CANCELLED})
        assert final.status is JobStatus.CANCELLED
    finally:
        release_blocker.set()
        manager.shutdown()


def test_event_sequence_success() -> None:
    manager = JobManager()
    events, unsubscribe = _collect_events(manager)
    try:
        job_id = manager.submit("work", _slow_work)
        _wait_for_status(manager, job_id, {JobStatus.SUCCEEDED})
    finally:
        manager.shutdown()
        unsubscribe()
    assert events == [
        JobEventType.CREATED,
        JobEventType.STARTED,
        JobEventType.SUCCEEDED,
    ]


def test_event_sequence_failure() -> None:
    manager = JobManager()
    events, unsubscribe = _collect_events(manager)
    try:
        job_id = manager.submit("work", _failing_work)
        _wait_for_status(manager, job_id, {JobStatus.FAILED})
    finally:
        manager.shutdown()
        unsubscribe()
    assert events == [
        JobEventType.CREATED,
        JobEventType.STARTED,
        JobEventType.FAILED,
    ]


def test_event_sequence_cancellation() -> None:
    manager = JobManager()
    events, unsubscribe = _collect_events(manager)
    try:
        job_id = manager.submit("work", _cooperative_work)
        _wait_for_status(manager, job_id, {JobStatus.RUNNING})
        manager.cancel(job_id)
        _wait_for_status(manager, job_id, {JobStatus.CANCELLED})
    finally:
        manager.shutdown()
        unsubscribe()
    assert events == [
        JobEventType.CREATED,
        JobEventType.STARTED,
        JobEventType.CANCELLATION_REQUESTED,
        JobEventType.CANCELLED,
    ]


def test_cancel_unknown_job_raises() -> None:
    manager = JobManager()
    try:
        with pytest.raises(JobError):
            manager.cancel("does-not-exist")
    finally:
        manager.shutdown()


def test_get_state_unknown_job_raises() -> None:
    manager = JobManager()
    try:
        with pytest.raises(JobError):
            manager.get_state("does-not-exist")
    finally:
        manager.shutdown()


def test_cancel_terminal_job_is_noop() -> None:
    manager = JobManager()
    try:
        job_id = manager.submit("work", _slow_work)
        _wait_for_status(manager, job_id, {JobStatus.SUCCEEDED})
        manager.cancel(job_id)  # must not raise
        assert manager.get_state(job_id).status is JobStatus.SUCCEEDED
    finally:
        manager.shutdown()


def test_shutdown_waits_for_running_job() -> None:
    manager = JobManager()
    job_id = manager.submit("work", _slow_work)
    _wait_for_status(manager, job_id, {JobStatus.RUNNING})
    manager.shutdown(wait=True)
    assert manager.get_state(job_id).status is JobStatus.SUCCEEDED


def test_bounded_work_completes_when_not_cancelled() -> None:
    manager = JobManager()
    try:
        job_id = manager.submit("work", _cooperative_bounded)
        final = _wait_for_status(manager, job_id, {JobStatus.SUCCEEDED})
        assert final.status is JobStatus.SUCCEEDED
    finally:
        manager.shutdown()


def test_submit_after_shutdown_raises_and_leaves_no_orphan() -> None:
    manager = JobManager()
    events, unsubscribe = _collect_events(manager)
    manager.shutdown()

    with pytest.raises(RuntimeError):
        manager.submit("work", _slow_work)

    unsubscribe()
    # No CREATED event emitted and no orphan PENDING job/token recorded.
    assert events == []
    assert manager._jobs == {}
    assert manager._tokens == {}


def test_shutdown_is_idempotent() -> None:
    manager = JobManager()
    manager.shutdown()
    manager.shutdown()  # must not raise
