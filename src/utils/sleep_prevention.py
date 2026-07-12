"""Utility for preventing computer sleep on macOS."""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class SleepPrevention:
    """Prevents the computer from sleeping while recording.

    Uses `caffeinate` on macOS to keep the system awake.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start preventing sleep."""
        if self._running:
            return

        self._running = True
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

    def _caffeinate_loop(self) -> None:
        """Keep caffeinate running while recording."""
        import time

        while self._running:
            if self._process is None or self._process.poll() is not None:
                try:
                    self._process = subprocess.Popen(
                        [
                            "caffeinate",
                            "-d",  # Prevent display sleep
                            "-w", str(__import__("os").getpid()),  # Keep awake for this process
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    logger.debug("caffeinate started with PID %d", self._process.pid)
                except FileNotFoundError:
                    logger.warning(
                        "caffeinate command not found. "
                        "Computer may sleep during recording."
                    )
                    break
                except OSError as e:
                    logger.warning("Failed to start caffeinate: %s", e)
                    break

            time.sleep(5)  # Check every 5 seconds
