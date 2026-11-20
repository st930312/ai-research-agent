"""One FIFO lane for NVIDIA HTTP attempts shared by concurrent services.

The lock is released after each attempt so HTTP retries, invalid-JSON retries,
and other services all take their turn without overlapping API calls.
"""
from __future__ import annotations

import os
import threading
import time


class AIRequestScheduler:
    def __init__(self, min_interval=None, clock=None, sleep=None):
        self.min_interval = max(
            0.0, float(os.getenv("NVIDIA_MIN_INTERVAL_SECONDS", "10"))
            if min_interval is None else float(min_interval)
        )
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._condition = threading.Condition()
        self._next_ticket = 0
        self._serving = 0
        self._next_start = 0.0

    def run(self, action, *, label="nvidia"):
        """FIFO admission; one active request, spacing measured at start."""
        with self._condition:
            ticket = self._next_ticket
            self._next_ticket += 1
            queued = self._clock()
            while ticket != self._serving:
                self._condition.wait()
            delay = max(0.0, self._next_start - self._clock())
            if delay:
                print(f"AI_QUEUE_DELAY model={label} seconds={delay:.1f}", flush=True)
                self._sleep(delay)
            start = self._clock()
            self._next_start = start + self.min_interval
            print(f"AI_QUEUE_START model={label} ticket={ticket} "
                  f"wait_s={start - queued:.2f}", flush=True)
            try:
                return action()
            finally:
                self._serving += 1
                self._condition.notify_all()
