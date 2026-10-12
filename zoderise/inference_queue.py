"""A bounded FIFO gate for the single Ollama worker on the host laptop."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterator


class InferenceQueue:
    def __init__(self, max_waiting: int = 16, wait_seconds: float = 300):
        self.max_waiting = max_waiting
        self.wait_seconds = wait_seconds
        self._condition = threading.Condition()
        self._waiting: list[tuple[object, int | None]] = []
        self._active_user: int | None = None
        self._busy = False

    def snapshot(self) -> dict[str, int | bool]:
        with self._condition:
            return {"busy": self._busy, "waiting": len(self._waiting)}

    @contextmanager
    def slot(self, user_id: int | None = None, on_wait: Callable[[int], None] | None = None) -> Iterator[None]:
        ticket = object()
        deadline = time.monotonic() + self.wait_seconds
        with self._condition:
            if len(self._waiting) >= self.max_waiting:
                raise RuntimeError("The AI queue is full. Please try again shortly.")
            if user_id is not None and (self._active_user == user_id or any(uid == user_id for _, uid in self._waiting)):
                raise RuntimeError("You already have an AI request in progress or waiting.")
            self._waiting.append((ticket, user_id))
            acquired = False
            try:
                last_position = None
                while True:
                    position = next(i for i, (token, _) in enumerate(self._waiting) if token is ticket)
                    if position == 0 and not self._busy:
                        self._waiting.pop(0)
                        self._busy = True
                        self._active_user = user_id
                        acquired = True
                        break
                    if on_wait and position != last_position:
                        # Callback runs outside the queue lock so Streamlit rendering cannot block others.
                        self._condition.release()
                        try:
                            on_wait(position)
                        finally:
                            self._condition.acquire()
                    last_position = position
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError("The AI queue waited too long. Please try again.")
                    self._condition.wait(timeout=min(remaining, 1.0))
            finally:
                if not acquired:
                    self._waiting = [(token, uid) for token, uid in self._waiting if token is not ticket]
                    self._condition.notify_all()
        try:
            yield
        finally:
            with self._condition:
                self._busy = False
                self._active_user = None
                self._condition.notify_all()


inference_queue = InferenceQueue()
