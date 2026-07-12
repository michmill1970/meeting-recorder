"""Main application window."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QInputDialog,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QDialog,
)

from src.models.schemas import MeetingStatus, RecordingSession
from src.settings.manager import Settings, SettingsManager
from src.ui.components.audio_meter import AudioMeter
from src.ui.components.recording_panel import RecordingPanel
from src.ui.components.summary_panel import SummaryPanel
from src.ui.components.settings_dialog import SettingsDialog
from src.ui.components.transcript_panel import TranscriptPanel

logger = logging.getLogger(__name__)


class TranscribeThread(QThread):
    """Thread for running Whisper transcription only."""

    progress = Signal(str)
    transcript_ready = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        session_dir: Path,
        audio_path: Path,
        whisper_client,
    ):
        super().__init__()
        self._session_dir = session_dir
        self._audio_path = audio_path
        self._whisper_client = whisper_client

    def run(self) -> None:
        """Run transcription."""
        import sys

        self._whisper_client.set_progress_callback(
            lambda msg: self.progress.emit(msg)
        )

        try:
            self.progress.emit("Starting transcription...")

            if not self._audio_path or not self._audio_path.exists():
                self.error.emit(f"Audio file not found: {self._audio_path}")
                return

            from src.models.schemas import RecordingSession

            session = RecordingSession()
            session.meeting_dir = self._session_dir
            session.audio_path = self._audio_path

            transcript = self._whisper_client.transcribe(self._audio_path, session)

            if transcript is None:
                self.error.emit("Transcription failed. Check logs for details.")
                return

            self.transcript_ready.emit(transcript)
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Error during processing: {e}")
            logger.exception("Processing thread error")


class SummarizeThread(QThread):
    """Thread for running LLM summarization only."""

    progress = Signal(str)
    summary_ready = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        transcript: str,
        llm_client,
    ):
        super().__init__()
        self._transcript = transcript
        self._llm_client = llm_client

    def run(self) -> None:
        """Run summarization."""
        import asyncio
        import sys

        try:
            self.progress.emit("Generating summary...")
            # Use a dedicated event loop to avoid conflicts with any existing loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary = loop.run_until_complete(
                    self._llm_client.summarize(self._transcript)
                )
            finally:
                loop.close()

            if summary is None:
                self.error.emit("Summarization failed. Check LLM configuration.")
                return

            self.summary_ready.emit(summary)
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Error during processing: {e}")
            logger.exception("Processing thread error")


class MainWindow(QMainWindow):
    """Main application window.

    Modern layout with clear visual hierarchy:
    - Top bar: Meeting name input
    - Left panel: Recording controls
    - Center: Transcript display
    - Bottom: Summary display
    - Status bar: Progress and status information
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._settings_manager = SettingsManager()
        self._session = None
        self._transcribe_thread: Optional[TranscribeThread] = None
        self._summarize_thread: Optional[SummarizeThread] = None
        self._pending_transcript: Optional[str] = None

        # Import here to avoid issues if modules aren't available
        from src.recording.engine import RecordingEngine
        from src.recording.level_manager import LevelManager
        from src.transcription.whisper_client import WhisperClient
        from src.summarization.llm_client import LLMClient
        from src.utils.sleep_prevention import SleepPrevention

        self._recording_engine = RecordingEngine(settings)
        self._level_manager = LevelManager(settings, self._recording_engine)
        self._whisper_client = WhisperClient(settings)
        self._llm_client = LLMClient(settings)
        self._sleep_prevention = SleepPrevention()

        self._setup_ui()
        self._connect_signals()
        self._load_microphones()

        # Timer for updating level metrics
        self._level_timer = QTimer(self)
        self._level_timer.setInterval(200)
        self._level_timer.timeout.connect(self._update_level_display)
        self._level_timer.start()

    def _setup_ui(self) -> None:
        """Set up the main window UI with modern layout."""
        self.setWindowTitle("Meeting Recorder")
        self.setMinimumSize(1100, 750)

        # Central widget with grid layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Top bar with meeting name - Modern input design
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        meeting_label = QLabel("Meeting:")
        meeting_label.setStyleSheet("color: #A0A0B0; font-size: 13px; font-weight: 500;")
        top_layout.addWidget(meeting_label)

        self._meeting_name_edit = QLineEdit()
        self._meeting_name_edit.setPlaceholderText("Enter meeting name (default: date-time)")
        default_name = __import__("datetime").datetime.now().strftime("%Y-%m-%d_%H-%M")
        self._meeting_name_edit.setText(default_name)
        self._meeting_name_edit.setMinimumHeight(36)
        top_layout.addWidget(self._meeting_name_edit)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Left panel - recording controls
        self._recording_panel = RecordingPanel()
        splitter.addWidget(self._recording_panel)
        splitter.setStretchFactor(0, 0)  # Fixed width

        # Center - transcript
        self._transcript_panel = TranscriptPanel()
        splitter.addWidget(self._transcript_panel)
        splitter.setStretchFactor(1, 2)  # Expands

        main_layout.addWidget(splitter)

        # Bottom panel - summary
        summary_frame = QVBoxLayout()
        summary_frame.setSpacing(6)

        summary_label = QLabel("Summary")
        summary_label.setObjectName("title")
        summary_label.setStyleSheet("font-size: 16px;")
        summary_frame.addWidget(summary_label)

        self._summary_panel = SummaryPanel()
        summary_frame.addWidget(self._summary_panel)

        main_layout.addLayout(summary_frame)

        # Status bar
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        self.statusBar().addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setFixedWidth(200)
        self.statusBar().addWidget(self._progress_bar)

        # Menu bar
        self._setup_menu()

    def _setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        export_action = QAction("&Export Meeting", self)
        export_action.triggered.connect(self._export_meeting)
        export_action.setEnabled(False)
        self._export_action = export_action
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("E&xit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers."""
        self._recording_panel.record_clicked.connect(self._on_record)
        self._recording_panel.pause_clicked.connect(self._on_pause)
        self._recording_panel.stop_clicked.connect(self._on_stop)
        self._recording_panel.mic_selected.connect(self._on_mic_selected)
        self._recording_panel.gain_changed.connect(self._on_gain_changed)
        self._recording_panel.auto_mode_toggled.connect(self._on_auto_mode_toggled)
        self._recording_panel.meeting_selected.connect(self._load_meeting)
        self._recording_panel.reprocess_clicked.connect(self._reprocess_meeting)

        # Connect tab switch to populate meetings list
        self._recording_panel._tabs.currentChanged.connect(self._on_tab_changed)

    def _load_microphones(self) -> None:
        """Load available microphones."""
        from src.recording.engine import RecordingEngine

        engine = RecordingEngine(self._settings)
        engine.initialize()
        devices = self._settings_manager.get_mic_device_info(engine._pa)  # type: ignore[attr-defined]
        engine.shutdown()
        self._recording_panel.set_microphones(devices)

        # Restore selected mic
        self._recording_panel.select_microphone(self._settings.recording.mic_device_id)

    # Recording handlers
    def _on_record(self) -> None:
        """Handle record button click."""
        meeting_name = self._meeting_name_edit.text().strip()
        if not meeting_name:
            meeting_name = __import__("datetime").datetime.now().strftime(
                "%Y-%m-%d_%H-%M"
            )

        from src.models.schemas import RecordingSession

        self._session = RecordingSession(
            name=meeting_name,
            save_dir=Path(self._settings.recording.save_dir),
        )

        # Set up level callback
        self._recording_engine.set_level_callback(
            lambda rms, peak: self._recording_panel.update_meter(rms, peak, 0.0)
        )

        # Start recording
        self._recording_engine.start(self._session)
        self._level_manager.start()
        self._sleep_prevention.start()

        # Start calibration
        self._level_manager._is_calibrating = True

        self._recording_panel.set_recording_state(True, False)
        self._transcript_panel.clear()
        self._summary_panel.clear()
        self._export_action.setEnabled(False)
        self._recording_panel.set_reprocess_enabled(False)

        self._status_label.setText(f"Recording: {meeting_name}")

    def _on_pause(self) -> None:
        """Handle pause/resume button click."""
        if self._recording_engine.is_paused:
            self._recording_engine.resume()
            self._level_manager._silence_start_time = None
        else:
            self._recording_engine.pause()

        self._recording_panel.set_recording_state(
            self._recording_engine.is_recording,
            self._recording_engine.is_paused,
        )

    def _on_stop(self) -> None:
        """Handle stop button click."""
        self._recording_engine.stop()
        self._level_manager.stop()
        self._sleep_prevention.stop()

        self._recording_panel.set_recording_state(False, False)
        self._recording_panel.set_reprocess_enabled(False)
        self._status_label.setText("Recording stopped")

        if self._session and self._session.audio_path:
            self._process_meeting()

    def _on_mic_selected(self, index: int) -> None:
        """Handle microphone selection."""
        self._settings.recording.mic_device_id = index
        self._settings_manager.save(self._settings)

    def _on_gain_changed(self, gain: float) -> None:
        """Handle manual gain change."""
        self._level_manager.set_gain(gain)

    def _on_auto_mode_toggled(self, is_auto: bool) -> None:
        """Handle auto mode toggle."""
        self._level_manager.is_auto_mode = is_auto
        if is_auto:
            self._level_manager.reset_auto_gain()
        self._recording_panel.set_gain_enabled(not is_auto)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change — populate meetings list when switching to Existing Recordings."""
        if index == 1:  # Existing Recordings tab
            self._populate_meetings_list()

    def _populate_meetings_list(self) -> None:
        """Scan the save directory and populate the meeting list."""
        save_dir = Path(self._settings.recording.save_dir)
        if not save_dir.exists():
            self._recording_panel.populate_meetings([])
            return

        meetings = []
        for meeting_dir in sorted(save_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not meeting_dir.is_dir():
                continue
            # Check if it has an audio file
            audio_files = list(meeting_dir.glob("recording.*"))
            if audio_files:
                audio_path = audio_files[0]
                format_ext = audio_path.suffix.lstrip(".")
                size_kb = audio_path.stat().st_size / 1024
                display = f"{meeting_dir.name}  ({size_kb:.0f} KB, .{format_ext})"
                meetings.append((display, str(meeting_dir)))

        self._recording_panel.populate_meetings(meetings)

    def _load_meeting(self, meeting_dir_str: str) -> None:
        """Load a selected meeting's transcript and summary into the panels.

        Args:
            meeting_dir_str: Path to the meeting directory
        """
        meeting_dir = Path(meeting_dir_str)
        if not meeting_dir.exists():
            QMessageBox.warning(self, "Meeting Not Found", f"Meeting directory not found:\n{meeting_dir}")
            return

        # Clear current display
        self._transcript_panel.clear()
        self._summary_panel.clear()
        self._export_action.setEnabled(False)

        # Read transcript if it exists
        transcript_path = meeting_dir / "transcript.txt"
        if transcript_path.exists():
            transcript = transcript_path.read_text(encoding="utf-8")
            self._transcript_panel.set_transcript(transcript)

        # Read summary if it exists
        summary_path = meeting_dir / "summary.md"
        if summary_path.exists():
            summary = summary_path.read_text(encoding="utf-8")
            self._summary_panel.set_summary(summary)
            self._export_action.setEnabled(True)

        # Store for export
        self._session = RecordingSession()
        self._session.meeting_dir = meeting_dir

        # Enable reprocess button
        self._recording_panel.set_reprocess_enabled(True)
        self._status_label.setText(f"Loaded: {meeting_dir.name}")

    def _reprocess_meeting(self) -> None:
        """Reprocess the currently selected meeting with current settings."""
        meeting_dir_str = self._recording_panel.get_selected_meeting_dir()
        if not meeting_dir_str:
            return

        meeting_dir = Path(meeting_dir_str)

        # Find audio file
        audio_files = list(meeting_dir.glob("recording.*"))
        if not audio_files:
            QMessageBox.warning(
                self,
                "No Audio File",
                f"No audio file found in:\n{meeting_dir}",
            )
            return

        audio_path = audio_files[0]

        # Start transcription
        self._transcribe_thread = TranscribeThread(
            meeting_dir,
            audio_path,
            self._whisper_client,
        )

        self._transcribe_thread.progress.connect(self._on_processing_progress)
        self._transcribe_thread.transcript_ready.connect(self._on_transcript_ready)
        self._transcribe_thread.error.connect(self._on_processing_error)
        self._transcribe_thread.finished.connect(self._on_processing_finished)

        self._status_label.setText("Reprocessing...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate

        self._transcribe_thread.start()

    # Processing
    def _process_meeting(self) -> None:
        """Start transcription."""
        self._transcribe_thread = TranscribeThread(
            self._session.meeting_dir,  # type: ignore[union-attr]
            self._session.audio_path,  # type: ignore[union-attr]
            self._whisper_client,
        )

        self._transcribe_thread.progress.connect(self._on_processing_progress)
        self._transcribe_thread.transcript_ready.connect(self._on_transcript_ready)
        self._transcribe_thread.error.connect(self._on_processing_error)
        self._transcribe_thread.finished.connect(self._on_processing_finished)

        self._status_label.setText("Processing...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate

        self._transcribe_thread.start()

    def _on_processing_progress(self, message: str) -> None:
        """Handle processing progress updates."""
        logger.info("[Processing] %s", message)
        self._status_label.setText(message)

    def _on_transcript_ready(self, transcript: str) -> None:
        """Handle transcript completion — show speaker rename dialog."""
        self._transcript_panel.set_transcript(transcript)
        self._pending_transcript = transcript

        # Show speaker rename dialog
        from src.ui.components.speaker_rename_dialog import SpeakerRenameDialog

        dialog = SpeakerRenameDialog(
            transcript_text=transcript,
            meeting_dir=self._session.meeting_dir,  # type: ignore[union-attr]
            parent=self,
        )

        # Connect dialog signals
        dialog.speakers_confirmed.connect(self._on_speakers_renamed)
        dialog.use_defaults.connect(self._on_use_default_speakers)
        dialog.cancelled.connect(self._on_speaker_rename_cancelled)

        # Show dialog
        dialog.exec()

        # Refresh transcript display in case speakers were renamed
        self._refresh_transcript_display()

    def _refresh_transcript_display(self) -> None:
        """Re-read and display the transcript from disk."""
        if self._session and self._session.meeting_dir:
            transcript_path = self._session.meeting_dir / "transcript.txt"
            if transcript_path.exists():
                updated = transcript_path.read_text(encoding="utf-8")
                self._transcript_panel.set_transcript(updated)
                self._pending_transcript = updated

    def _on_speakers_renamed(self, renames: list[tuple[str, str]]) -> None:
        """Handle speaker renaming — proceed with summarization."""
        logger.info("Speakers renamed: %s", renames)
        self._proceed_with_summarization()

    def _on_use_default_speakers(self) -> None:
        """Handle use default speakers — proceed with summarization."""
        logger.info("Using default speaker labels")
        self._proceed_with_summarization()

    def _on_speaker_rename_cancelled(self) -> None:
        """Handle speaker rename cancellation — stop processing."""
        self._status_label.setText("Processing cancelled")
        self._progress_bar.setVisible(False)
        self._transcript_panel.clear()
        self._summary_panel.clear()
        self._session = None

    def _proceed_with_summarization(self) -> None:
        """Start LLM summarization after speaker rename decision."""
        # Re-read from disk in case the rename dialog updated it
        if self._session and self._session.meeting_dir:
            transcript_path = self._session.meeting_dir / "transcript.txt"
            if transcript_path.exists():
                transcript = transcript_path.read_text(encoding="utf-8")
            else:
                transcript = getattr(self, "_pending_transcript", None)
        else:
            transcript = getattr(self, "_pending_transcript", None)

        if not transcript:
            QMessageBox.critical(
                self,
                "No Transcript",
                "No transcript available for summarization.\n\n"
                "Please record a meeting or load an existing one first.",
            )
            self._progress_bar.setVisible(False)
            return

        self._summarize_thread = SummarizeThread(
            transcript,
            self._llm_client,
        )

        self._summarize_thread.progress.connect(self._on_processing_progress)
        self._summarize_thread.summary_ready.connect(self._on_summary_ready)
        self._summarize_thread.error.connect(self._on_processing_error)
        self._summarize_thread.finished.connect(self._on_processing_finished)

        self._status_label.setText("Generating summary...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate

        self._summarize_thread.start()

    def _on_summary_ready(self, summary: str) -> None:
        """Handle summary completion."""
        self._summary_panel.set_summary(summary)

        # Save summary to file
        if self._session and self._session.meeting_dir:
            summary_path = self._session.meeting_dir / "summary.md"
            summary_path.write_text(summary, encoding="utf-8")
            self._session.summary_path = summary_path

        self._export_action.setEnabled(True)
        self._status_label.setText("Processing complete")

    def _on_processing_error(self, error_msg: str) -> None:
        """Handle processing error."""
        self._status_label.setText("Error")
        self._progress_bar.setVisible(False)

        reply = QMessageBox.question(
            self,
            "Processing Error",
            f"{error_msg}\n\nDo you want to try again?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._process_meeting()

    def _on_processing_finished(self) -> None:
        """Handle processing thread completion."""
        self._progress_bar.setVisible(False)

    # Utility
    def _update_level_display(self) -> None:
        """Update level display from level manager."""
        if self._recording_engine.is_recording:
            metrics = self._level_manager.get_level_metrics()
            self._recording_panel.update_meter(
                metrics["rms_db"],
                metrics["peak_db"],
                metrics["gain_db"],
            )
            self._recording_panel.set_meter_calibration(
                bool(metrics["is_calibrating"]),
                bool(metrics["is_auto_mode"]),
            )
            self._status_label.setText(
                f"Recording | Elapsed: {self._session.elapsed_formatted if self._session else '00:00'} | "
                + self._recording_panel._meter.get_level_text()  # type: ignore[attr-defined]
            )

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == QDialog.Accepted:
            self._settings_manager.save(self._settings)
            # Reload from disk to get properly-typed enum values
            self._settings = self._settings_manager.load()
            # Update clients with new settings
            from src.transcription.whisper_client import WhisperClient
            from src.summarization.llm_client import LLMClient

            self._whisper_client = WhisperClient(self._settings)
            self._llm_client = LLMClient(self._settings)
            self._status_label.setText("Settings saved")

    def _export_meeting(self) -> None:
        """Export meeting as ZIP."""
        if not self._session or not self._session.meeting_dir:
            return

        from src.utils.export import export_meeting_zip

        zip_path = export_meeting_zip(self._session.meeting_dir)
        if zip_path:
            self._status_label.setText(f"Exported to {zip_path}")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Meeting exported to:\n{zip_path}",
            )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Handle window close."""
        self._recording_engine.stop()
        self._level_manager.stop()
        self._sleep_prevention.stop()
        self._settings_manager.save(self._settings)
        event.accept()
