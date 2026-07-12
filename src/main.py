"""Main entry point for the Meeting Recorder application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.settings.manager import Settings, SettingsManager
from src.ui.main_window import MainWindow
from src.ui.styles.dark_theme import DARK_THEME  # type: ignore[import-untyped]


def setup_logging() -> None:
    """Configure application logging."""
    log_dir = Path.home() / ".config" / "meeting-recorder"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "meeting-recorder.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Meeting Recorder...")

    app = QApplication(sys.argv)
    app.setApplicationName("Meeting Recorder")
    app.setOrganizationName("MeetingRecorder")

    # Load settings
    settings_manager = SettingsManager()
    settings = settings_manager.load()

    # Apply dark theme
    app.setStyleSheet(DARK_THEME)

    # Create and show main window
    window = MainWindow(settings)
    window.show()

    logger.info("Meeting Recorder started")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
