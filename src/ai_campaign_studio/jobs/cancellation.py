"""Cooperative cancellation primitives (P0.20).

Owns the thread-safe ``CancellationToken`` and the ``CancellationError`` a
cancel-aware callable raises via ``raise_if_cancelled``. Does not force-stop
threads (cooperative only) and does not depend on any GUI framework.
"""

from __future__ import annotations

import threading


class CancellationError(Exception):
    """Raised by ``CancellationToken.raise_if_cancelled`` on cancellation.

    ``JobManager`` catches this specific type and transitions the job to
    ``CANCELLED`` instead of ``FAILED``.
    """


class CancellationToken:
    """Thread-safe cooperative cancellation flag.

    Built on ``threading.Event`` so ``request_cancel``/``is_cancel_requested``
    are safe to call from any thread. It never interrupts a running callable;
    the callable must check ``raise_if_cancelled`` (or ``is_cancel_requested``)
    at cooperative points.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def request_cancel(self) -> None:
        """Signal cancellation. Idempotent."""
        self._event.set()

    def is_cancel_requested(self) -> bool:
        """Return True once cancellation has been requested."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise ``CancellationError`` if cancellation was requested."""
        if self._event.is_set():
            raise CancellationError()
