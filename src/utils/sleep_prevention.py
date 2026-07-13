"""Utility for preventing computer sleep on macOS.

Uses `caffeinate` on macOS to keep the system awake during recording.
Retries on transient failures with exponential backoff instead of
permanently disabling sleep prevention on first error.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class SleepPrevention:
    """Prevents the computer from sleeping while recording.

    Uses `caffeinate` on macOS to keep the system awake.
    Retries with exponential backoff on transient failures.
    """

    # Maximum number of consecutive failures before giving up
    _MAX_FAILURES = 10
    # Base sleep interval for backoff (seconds)
    _BACKOFF_BASE = 5
    # Maximum backoff interval (seconds)
    _BACKOFF_MAX = 60

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._consecutive_failures = 0

    def start(self) -> None:
        """Start preventing sleep."""
        if self._running:
            return

        self._running = True
        self._consecutive_failures = 0
        self._thread = threading.Thread(target=self._caffeinate_loop, daemon=True)
        self._thread.start()
        logger.info("Sleep prevention started")

    def stop(self) -> None:
        """Stop preventing sleep."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception as e:
                logger.warning("Error terminating caffeinate: %s", e)
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Sleep prevention stopped")

    def _backoff_delay(self) -> float:
        """Calculate backoff delay with exponential growth capped at _BACKOFF_MAX."""
        delay = min(
            self._BACKOFF_BASE * (2 ** self._consecutive_failures),
            self._BACKOFF_MAX,
        )
        return delay

    def _caffeinate_loop(self) -> None:
        """Keep caffeinate running while recording.

        Retries on transient failures with exponential backoff.
        Only gives up after _MAX_FAILURES consecutive failures.
        """
        while self._running:
            if self._process is None or self._process.poll() is not None:
                try:
                    self._process = subprocess.Popen(
                        [
                            "caffeinate",
                            "-d",  # Prevent display sleep
                            "-w", str(os.getpid()),  # Keep awake for this process
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    logger.debug("caffeinate started with PID %d", self._process.pid)
                    self._consecutive_failures = 0  # Reset on success
                except FileNotFoundError:
                    self._consecutive_failures += 1
                    if self._consecutive_failures == 1:
                        logger.warning(
                            "caffeinate command not found. "
                            "Computer may sleep during recording."
                        )
                    elif self._consecutive_failures >= self._MAX_FAILURES:
                        logger.error(
                            "caffeinate failed %d times; sleep prevention disabled.",
                            self._consecutive_failures,
                        )
                        break
                    else:
                        logger.debug(
                            "caffeinate not found, retry %d/%d",
                            self._consecutive_failures,
                            self._MAX_FAILURES,
                        )
                except OSError as e:
                    self._consecutive_failures += 1
                    if self._consecutive_failures == 1:
                        logger.warning("Failed to start caffeinate: %s", e)
                    elif self._consecutive_failures >= self._MAX_FAILURES:
                        logger.error(
                            "caffeinate failed %d times; sleep prevention disabled.",
                            self._consecutive_failures,
                        )
                        break
                    else:
                        logger.debug(
                            "caffeinate failed (%s), retry %d/%d",
                            e,
                            self._consecutive_failures,
                            self._MAX_FAILURES,
                        )

            # Sleep with backoff that grows on consecutive failures
            delay = self._backoff_delay() if self._consecutive_failures > 0 else 5
            self._sleep(delay)

    def _sleep(self, seconds: float) -> None:
        """Sleep wrapper — overridable for testing."""
        time.sleep(seconds)
