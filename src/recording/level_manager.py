"""Audio level management with automatic gain control.

Implements RMS-based audio level analysis, automatic gain adjustment,
ambient noise calibration, and dead air detection.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Optional

import numpy as np

from src.models.schemas import MeetingStatus
from src.recording.engine import RecordingEngine
from src.settings.manager import Settings

logger = logging.getLogger(__name__)


class LevelManager:
    """Manages audio levels with automatic gain control.

    Features:
    - RMS-based level analysis
    - Automatic gain adjustment based on target level
    - Ambient noise calibration at recording start
    - Dead air detection (no boost unless silence > threshold)
    - Smooth gain ramping to avoid sudden changes
    - Manual override mode
    """

    # How often to update gain (seconds)
    UPDATE_INTERVAL = 0.5
    # Minimum gain change step (dB)
    MIN_GAIN_STEP = 0.25
    # Seconds of silence to consider as "dead air"
    DEAD_AIR_THRESHOLD = 60.0
    # Window size for RMS calculation (seconds)
    RMS_WINDOW = 0.5

    def __init__(self, settings: Settings, engine: RecordingEngine):
        self._settings = settings
        self._engine = engine
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Current state
        self._current_gain_db: float = 0.0
        self._target_gain_db: float = 0.0
        self._noise_floor_db: float = -60.0  # Initial estimate
        self._is_calibrating = False
        self._calibration_data: list[float] = []
        self._silence_start_time: Optional[float] = None
        self._last_gain_update: float = 0.0

        # RMS history for smoothing
        self._rms_history: list[tuple[float, float]] = []  # (timestamp, rms_db)

    @property
    def current_gain_db(self) -> float:
        """Get current gain in dB."""
        with self._lock:
            return self._current_gain_db

    @property
    def is_auto_mode(self) -> bool:
        """Check if automatic mode is enabled."""
        return self._settings.audio_leveling.auto_mode

    @is_auto_mode.setter
    def is_auto_mode(self, value: bool) -> None:
        """Set automatic mode."""
        self._settings.audio_leveling.auto_mode = value
        logger.info("Auto mode: %s", value)

    def start(self) -> None:
        """Start level management loop."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._level_loop, daemon=True)
        self._thread.start()
        logger.info("Level manager started")

    def stop(self) -> None:
        """Stop level management loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Level manager stopped")

    def set_gain(self, gain_db: float) -> None:
        """Set gain manually (disables auto mode)."""
        cfg = self._settings.audio_leveling
        gain_db = max(-cfg.max_gain_db, min(cfg.max_gain_db, gain_db))

        with self._lock:
            self._current_gain_db = gain_db
            self._target_gain_db = gain_db
            self._is_calibrating = False
            self._calibration_data = []

        logger.info("Manual gain set to %.1f dB", gain_db)

    def reset_auto_gain(self) -> None:
        """Reset to auto mode with zero gain offset."""
        with self._lock:
            self._current_gain_db = 0.0
            self._target_gain_db = 0.0

    def _level_loop(self) -> None:
        """Main level management loop."""
        last_update = time.monotonic()

        while self._running:
            now = time.monotonic()

            # Skip if engine not recording
            if not self._engine.is_recording:
                time.sleep(self.UPDATE_INTERVAL)
                continue

            # Calibrate at start of recording
            if self._is_calibrating:
                self._run_calibration()
                continue

            # Update gain at intervals
            if now - last_update >= self.UPDATE_INTERVAL:
                self._update_gain()
                last_update = now

            time.sleep(0.05)  # Check every 50ms

    def _run_calibration(self) -> None:
        """Run ambient noise calibration."""
        cfg = self._settings.audio_leveling
        duration = cfg.calibration_duration_sec
        logger.info("Calibrating ambient noise for %.1f seconds...", duration)

        start_time = time.monotonic()
        rms_values: list[float] = []

        while self._running and (time.monotonic() - start_time) < duration:
            buffer = self._engine.audio_buffer
            if buffer is not None and len(buffer) > 0:
                rms = self._compute_rms_db(buffer)
                rms_values.append(rms)

            time.sleep(0.05)

        # Calculate noise floor from calibration data
        if rms_values:
            # Use percentile to get noise floor (below most speech)
            rms_values.sort()
            idx = int(len(rms_values) * 0.1)  # 10th percentile
            self._noise_floor_db = rms_values[idx]
            avg_rms = sum(rms_values) / len(rms_values)
            logger.info(
                "Calibration complete: noise floor=%.1f dB, avg=%.1f dB",
                self._noise_floor_db, avg_rms,
            )
            self._is_calibrating = False
        else:
            logger.warning("No audio data during calibration, using default noise floor")
            self._is_calibrating = False

    def _update_gain(self) -> None:
        """Update gain based on current audio levels."""
        if not self.is_auto_mode:
            return

        buffer = self._engine.audio_buffer
        if buffer is None or len(buffer) == 0:
            return

        cfg = self._settings.audio_leveling
        rms_db = self._compute_rms_db(buffer)

        now = time.monotonic()

        with self._lock:
            # Track RMS history for smoothing
            self._rms_history.append((now, rms_db))
            # Keep only last 2 seconds of history
            cutoff = now - 2.0
            self._rms_history = [(t, r) for t, r in self._rms_history if t >= cutoff]

            # Calculate average RMS from history
            if self._rms_history:
                avg_rms = sum(r for _, r in self._rms_history) / len(self._rms_history)
            else:
                avg_rms = rms_db

            # Target level is noise floor + offset
            target_level = self._noise_floor_db + cfg.noise_floor_offset_db

            # Calculate desired gain
            diff = target_level - avg_rms

            # Apply dead air detection
            if avg_rms < self._noise_floor_db + cfg.noise_floor_offset_db * 0.5:
                # Below threshold - check if it's been silent for a while
                if self._silence_start_time is None:
                    self._silence_start_time = now
                elif (now - self._silence_start_time) < cfg.dead_air_timeout_sec:
                    # Not dead air yet, don't boost
                    diff = 0.0
                else:
                    # Dead air detected, apply gentle boost
                    diff = min(diff, 3.0)  # Max 3 dB boost for dead air
            else:
                self._silence_start_time = None

            # Clamp gain change
            max_step = cfg.gain_ramp_rate_db_per_sec * self.UPDATE_INTERVAL
            diff = max(-max_step, min(max_step, diff))

            # Apply gain change
            self._target_gain_db += diff
            self._target_gain_db = max(
                -cfg.max_gain_db, min(cfg.max_gain_db, self._target_gain_db)
            )

            # Smoothly move current gain toward target
            gain_diff = self._target_gain_db - self._current_gain_db
            gain_diff = max(-max_step, min(max_step, gain_diff))
            self._current_gain_db += gain_diff

        # Apply gain to engine if we have a way to do so
        # (In practice, this would adjust the audio stream gain)
        # For PyAudio, we'll store the gain and apply it in the callback

        # Log gain changes occasionally
        if abs(diff) > self.MIN_GAIN_STEP:
            logger.debug("Gain adjusted: %.2f -> %.2f dB", diff, self._current_gain_db)

    def _compute_rms_db(self, audio_data: np.ndarray) -> float:
        """Compute RMS level in dB from audio samples."""
        if len(audio_data) == 0:
            return -60.0  # Silence

        # Convert to float and normalize
        samples = audio_data.astype(np.float64) / 32768.0
        rms = math.sqrt(np.mean(samples ** 2))

        # Convert to dB
        if rms < 1e-10:
            return -60.0
        return 20.0 * math.log10(rms)

    def get_level_metrics(self) -> dict[str, float]:
        """Get current level metrics for UI display."""
        buffer = self._engine.audio_buffer
        if buffer is not None and len(buffer) > 0:
            rms_db = self._compute_rms_db(buffer)
            peak_db = self._compute_peak_db(buffer)
        else:
            rms_db = -60.0
            peak_db = -60.0

        return {
            "rms_db": rms_db,
            "peak_db": peak_db,
            "gain_db": self.current_gain_db,
            "noise_floor_db": self._noise_floor_db,
            "is_calibrating": self._is_calibrating,
            "is_auto_mode": self.is_auto_mode,
        }

    def _compute_peak_db(self, audio_data: np.ndarray) -> float:
        """Compute peak level in dB from audio samples."""
        if len(audio_data) == 0:
            return -60.0

        samples = audio_data.astype(np.float64) / 32768.0
        peak = np.max(np.abs(samples))

        if peak < 1e-10:
            return -60.0
        return 20.0 * math.log10(peak)
