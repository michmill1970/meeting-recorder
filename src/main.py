"""Main entry point for the Meeting Recorder application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.settings.manager import Settings, SettingsManager
from src.settings.passphrase_manager import PassphraseManager
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

    # Initialize passphrase manager (tries keychain first)
    passphrase_manager = PassphraseManager()
    passphrase = passphrase_manager.get_passphrase()

    # Load settings (without passphrase first — needed to read encryption_enabled)
    settings_manager = SettingsManager(
        passphrase_manager=passphrase_manager
    )
    settings = settings_manager.load(passphrase=None)

    # If encryption is enabled but the keychain didn't provide a passphrase,
    # prompt the user so we can decrypt the stored credentials.
    if settings.encryption_enabled and not passphrase:
        logger.info("Encryption is enabled but no passphrase found in keychain — prompting user")
        passphrase = passphrase_manager.prompt_passphrase()
        if passphrase:
            passphrase_manager.set_passphrase(passphrase)
            # Reload settings with the provided passphrase
            settings = settings_manager.load(passphrase=passphrase)
        else:
            # User cancelled — settings will load with encrypted values
            # The Security tab will show encryption enabled and prompt again
            logger.warning("No passphrase provided — settings with encrypted credentials may not work correctly")

    # Apply dark theme
    app.setStyleSheet(DARK_THEME)

    # Create and show main window
    window = MainWindow(settings)
    window.show()

    logger.info("Meeting Recorder started")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
