"""Real-time audio meter visualization component."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class AudioMeter(QWidget):
    """Custom widget for displaying real-time audio levels.

    Modern design with smooth gradients, clear visual hierarchy,
    and accessible color coding.
    """

    # Color thresholds (dBFS)
    GREEN_MAX = -12.0
    YELLOW_MAX = -3.0
    # Below this is considered silence
    SILENCE_THRESHOLD = -60.0

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._rms_db: float = -60.0
        self._peak_db: float = -60.0
        self._gain_db: float = 0.0
        self._is_calibrating = False
        self._is_auto_mode = True

        # Animation
        self._display_rms = -60.0
        self._display_peak = -60.0
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(50)
        self._update_timer.timeout.connect(self._animate)
        self._update_timer.start()

        self.setFixedHeight(36)
        self.setMinimumWidth(200)

    def update_levels(self, rms_db: float, peak_db: float, gain_db: float = 0.0) -> None:
        """Update the meter with new level values."""
        self._rms_db = rms_db
        self._peak_db = peak_db
        self._gain_db = gain_db
        self.update()

    def set_calibration_state(self, is_calibrating: bool, is_auto_mode: bool) -> None:
        """Update calibration and auto mode state."""
        self._is_calibrating = is_calibrating
        self._is_auto_mode = is_auto_mode
        self.update()

    def _animate(self) -> None:
        """Smoothly animate meter display values."""
        smoothing = 0.3
        new_rms = self._display_rms + (self._rms_db - self._display_rms) * smoothing
        new_peak = self._display_peak + (self._display_peak - self._display_peak) * smoothing

        if abs(new_rms - self._display_rms) > 0.1 or abs(new_peak - self._display_peak) > 0.1:
            self._display_rms = new_rms
            self._display_peak = new_peak
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Paint the audio meter with modern design."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        padding = 6

        # Background with subtle gradient
        bg_color = QColor("#1A1A26")
        painter.fillRect(rect, bg_color)

        # Meter bar dimensions
        bar_rect = rect.adjusted(padding, padding, -padding, -padding)
        bar_height = bar_rect.height()
        bar_width = bar_rect.width()

        # Map dB range to bar width (-60 to 0 dB)
        db_range = 60.0  # -60 to 0
        effective_rms = max(self._display_rms, -60.0)
        fill_ratio = min(max((effective_rms + 60.0) / db_range, 0.0), 1.0)

        # Draw RMS bar with gradient
        rms_fill_width = int(bar_width * fill_ratio)
        if rms_fill_width > 0:
            rms_color = self._get_color_for_level(self._display_rms)
            gradient = QColor(rms_color)
            gradient.setAlpha(200)
            painter.fillRect(
                bar_rect.left(),
                bar_rect.top() + bar_height * 0.35,
                rms_fill_width,
                int(bar_height * 0.5),
                gradient,
            )

        # Draw peak indicator with smooth animation
        peak_fill_ratio = min(max((self._display_peak + 60.0) / db_range, 0.0), 1.0)
        peak_x = bar_rect.left() + int(bar_width * peak_fill_ratio)
        painter.setPen(QPen(QColor("#F87171"), 2))
        painter.drawLine(
            peak_x,
            bar_rect.top(),
            peak_x,
            bar_rect.bottom(),
        )

        # Calibration indicator with pulse effect
        if self._is_calibrating:
            painter.setPen(QPen(QColor("#4ADE80"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(bar_rect.adjusted(-2, -2, -2, -2))

        painter.end()

    def _get_color_for_level(self, db: float) -> QColor:
        """Get color based on dB level with modern palette."""
        if db < self.GREEN_MAX:
            return QColor("#4ADE80")  # Green - good level
        elif db < self.YELLOW_MAX:
            return QColor("#FBBF24")  # Yellow - watch out
        else:
            return QColor("#F87171")  # Red - clipping

    def get_level_text(self) -> str:
        """Get formatted level text for status bar."""
        parts = []
        parts.append(f"RMS: {self._rms_db:.1f} dB")
        parts.append(f"Peak: {self._peak_db:.1f} dB")
        parts.append(f"Gain: {self._gain_db:+.1f} dB")
        return " | ".join(parts)
