"""CancelToken: HTTP-level abort for long LLM calls.

A CancelToken bridges cooperative cancellation (task_manager) with
transport-level abort. When cancel() is called, it sets the Event AND
closes the underlying httpx client, which force-kills in-flight TCP
connections to the LLM provider.

Usage:
    token = CancelToken()
    http_client = httpx.Client(...)
    token.bind(http_client)          # give the token a handle to close
    adapter = create_adapter(..., cancel_token=token)

    # From another thread (e.g. cancel endpoint):
    token.cancel()                   # sets flag + closes connections
    token.raise_if_set()             # raises TaskCancelledError if cancelled
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from novel_generator.task_manager import TaskCancelledError

logger = logging.getLogger(__name__)


class CancelToken:
    """Thread-safe cancellation token with HTTP-level abort capability."""

    def __init__(self):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._http_clients: list = []
        self._cancelled = False

    # ── state queries ──────────────────────────────────────────────

    def is_set(self) -> bool:
        return self._event.is_set() or self._cancelled

    @property
    def cancelled(self) -> bool:
        return self.is_set()

    # ── bind / unbind httpx clients ─────────────────────────────────

    def bind(self, http_client) -> None:
        """Register an httpx.Client (or compatible) so cancel() can close it."""
        if http_client is None:
            return
        with self._lock:
            self._http_clients.append(http_client)

    # ── cancel ─────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Request cancellation AND force-close all bound HTTP clients.

        Closing the httpx clients terminates in-flight TCP connections,
        causing pending LLM adapter calls to fail fast.
        """
        if self._cancelled:
            return
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
            self._event.set()
            clients = list(self._http_clients)
            self._http_clients.clear()
        for client in clients:
            try:
                client.close()
            except Exception:
                logger.debug("Error closing http client during cancel", exc_info=True)

    # ── check ──────────────────────────────────────────────────────

    def raise_if_set(self, label: str = "任务") -> None:
        if self.is_set():
            raise TaskCancelledError(f"{label}已取消")

    # ── callable form for cancel_check ─────────────────────────────

    def __call__(self) -> bool:
        return self.is_set()
