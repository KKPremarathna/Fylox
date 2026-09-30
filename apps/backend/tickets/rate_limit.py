"""
Sliding-window log rate limiter for the AI category-suggestion endpoint.

Mechanism — sliding-window log:
    Every accepted call appends a monotonic timestamp to a per-user deque (the
    "log").  On each new request the log is first pruned of entries that have
    fallen outside the current [now - WINDOW, now] interval.  The remaining log
    length is then compared against LIMIT; if the log is already full the
    request is rejected with HTTP 429 and a Retry-After header computed from
    the age of the oldest surviving entry.

NOTE: This in-memory limiter is development-only and does not share state
across Uvicorn workers or application instances; production needs Redis or
equivalent centralized atomic storage (e.g. a Redis sorted-set script using
ZADD + ZREMRANGEBYSCORE + ZCOUNT evaluated atomically via a Lua script, or
a sliding-window log stored in PostgreSQL).
"""

import time
from collections import deque

from fastapi import HTTPException, status

# Configuration
LIMIT: int = 10        # maximum requests per window per user
WINDOW: float = 60.0   # rolling window length in seconds

# Internal log store: user_id -> deque of accepted call timestamps
_store: dict[int, deque[float]] = {}


def get_current_time() -> float:
    """
    Thin wrapper around time.monotonic().

    Routing code passes this function *by reference* as now_fn so that tests
    can monkeypatch ``backend.tickets.routes.get_current_time`` (the name
    bound in the routes module's namespace) without touching the default
    argument of any function — default arguments are bound at definition time
    and cannot be changed by patching after import.
    """
    return time.monotonic()


class SlidingWindowLogRateLimiter:
    """
    Per-user sliding-window log limiter.

    Each user has an independent deque.  Accepted timestamps are appended;
    expired timestamps (older than ``window`` seconds from ``now``) are pruned
    from the left before every decision.
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window

    def check(self, user_id: int, *, now_fn: "() -> float") -> None:
        """
        Inspect and update the sliding-window log for *user_id*.

        Raises HTTP 429 (with Retry-After) if the log is full.
        Appends the current timestamp to the log on success.

        Parameters
        ----------
        user_id:
            Unique identifier of the authenticated caller.
        now_fn:
            Callable that returns the current monotonic time as a float.
            Must be supplied by the caller so that the value is evaluated at
            call time, not bound at function-definition time.
        """
        now: float = now_fn()
        log: deque[float] = _store.setdefault(user_id, deque())

        # Prune log entries that have expired out of the current window.
        while log and now - log[0] >= self.window:
            log.popleft()

        if len(log) >= self.limit:
            # Seconds until the oldest surviving entry exits the window.
            retry_after: int = int(self.window - (now - log[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. You may make {self.limit} AI "
                    f"category suggestions per {int(self.window)}-second window."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        log.append(now)

    def reset(self) -> None:
        """Clear all per-user logs — intended for use in tests only."""
        _store.clear()


# Module-level singleton shared by all requests within a single process.
_limiter = SlidingWindowLogRateLimiter(limit=LIMIT, window=WINDOW)


def check_ai_suggestion_rate_limit(user_id: int, *, now_fn: "() -> float") -> None:
    """
    Public entry point called by the route handler.

    The caller must pass ``now_fn`` explicitly (never rely on a default here)
    so that the function object resolved from the caller's module namespace is
    used — making it patchable in tests via monkeypatch on the caller's
    imported name.
    """
    _limiter.check(user_id, now_fn=now_fn)


def reset_rate_limiter() -> None:
    """Clear all rate-limit state.  Call this in test fixtures."""
    _limiter.reset()
