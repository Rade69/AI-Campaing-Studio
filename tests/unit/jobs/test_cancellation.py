"""Unit tests for CancellationToken (P0.20)."""

import threading

import pytest

from ai_campaign_studio.jobs.cancellation import CancellationError, CancellationToken


def test_not_cancelled_initially() -> None:
    token = CancellationToken()
    assert token.is_cancel_requested() is False
    token.raise_if_cancelled()  # no-op when not requested


def test_request_cancel_sets_flag_and_raises() -> None:
    token = CancellationToken()
    token.request_cancel()
    assert token.is_cancel_requested() is True
    with pytest.raises(CancellationError):
        token.raise_if_cancelled()


def test_request_cancel_is_idempotent() -> None:
    token = CancellationToken()
    token.request_cancel()
    token.request_cancel()
    assert token.is_cancel_requested() is True


def test_token_is_thread_safe() -> None:
    token = CancellationToken()
    observed: list[bool] = []

    def worker() -> None:
        token.request_cancel()
        observed.append(token.is_cancel_requested())

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert observed == [True]
    assert token.is_cancel_requested() is True
