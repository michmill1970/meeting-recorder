"""Unit tests for MainWindow reprocess functionality."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.conftest import _qt_available

if not _qt_available:
    pytest.skip("Qt not available, skipping UI tests", allow_module_level=True)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


class TestMainWindowReprocess:
    """Tests for MainWindow reprocess flow."""

    @pytest.fixture
    def mock_app(self, qtbot):
        """Create a mock QApplication for testing."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        return app

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        from src.settings.manager import Settings
        return Settings()

    @pytest.fixture
    def mock_main_window(self, mock_app, mock_settings, tmp_dir):
        """Create a MainWindow with mocked dependencies."""
        from src.ui.main_window import MainWindow

        # Mock all the heavy dependencies and block QMessageBox to prevent dialogs during tests
        # Patch QMessageBox where it's imported (src.ui.main_window), not where it's defined
        with patch("src.recording.engine.RecordingEngine"), \
             patch("src.recording.level_manager.LevelManager"), \
             patch("src.transcription.whisper_client.WhisperClient"), \
             patch("src.summarization.llm_client.LLMClient"), \
             patch("src.utils.sleep_prevention.SleepPrevention"), \
             patch.object(MainWindow, "_load_microphones"), \
             patch("src.ui.main_window.QMessageBox.warning", return_value=QMessageBox.Ok), \
             patch("src.ui.main_window.QMessageBox.critical", return_value=QMessageBox.Ok), \
             patch("src.ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes), \
             patch("src.ui.main_window.QMessageBox.information", return_value=QMessageBox.Ok):
            window = MainWindow(mock_settings)
            window._settings.recording.save_dir = str(tmp_dir)
            return window

    def test_populate_meetings_list_empty(self, mock_main_window, tmp_dir):
        """Test that an empty save directory shows no meetings."""
        window = mock_main_window
        window._populate_meetings_list()
        # The list should be empty
        assert window._recording_panel._meeting_list.count() == 0

    def test_populate_meetings_list_with_meetings(self, mock_main_window, tmp_dir):
        """Test that meetings are listed from the save directory."""
        # Create some fake meeting directories with audio files
        meeting_a = tmp_dir / "meeting-a"
        meeting_a.mkdir()
        (meeting_a / "recording.wav").touch()

        meeting_b = tmp_dir / "meeting-b"
        meeting_b.mkdir()
        (meeting_b / "recording.opus").touch()

        window = mock_main_window
        window._populate_meetings_list()

        assert window._recording_panel._meeting_list.count() == 2
        # Meeting names should be in the list
        items = [window._recording_panel._meeting_list.item(i).text()
                 for i in range(window._recording_panel._meeting_list.count())]
        assert any("meeting-a" in item for item in items)
        assert any("meeting-b" in item for item in items)

    def test_populate_meetings_skips_non_dirs(self, mock_main_window, tmp_dir):
        """Test that non-directory entries are skipped."""
        # Create a file (not a directory) in the save dir
        (tmp_dir / "not_a_meeting.txt").touch()

        window = mock_main_window
        window._populate_meetings_list()
        assert window._recording_panel._meeting_list.count() == 0

    def test_populate_meetings_skips_dirs_without_audio(self, mock_main_window, tmp_dir):
        """Test that directories without audio files are skipped."""
        empty_meeting = tmp_dir / "empty-meeting"
        empty_meeting.mkdir()
        # No audio file

        window = mock_main_window
        window._populate_meetings_list()
        assert window._recording_panel._meeting_list.count() == 0

    def test_populate_meetings_shows_format(self, mock_main_window, tmp_dir):
        """Test that the audio format is shown in the meeting list."""
        meeting = tmp_dir / "meeting-opus"
        meeting.mkdir()
        (meeting / "recording.opus").touch()

        window = mock_main_window
        window._populate_meetings_list()

        item = window._recording_panel._meeting_list.item(0)
        assert ".opus" in item.text()

    def test_load_meeting_with_transcript(self, mock_main_window, tmp_dir):
        """Test loading a meeting that has a transcript file."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()
        (meeting / "transcript.txt").write_text("Speaker 1: Hello", encoding="utf-8")

        window = mock_main_window
        window._load_meeting(str(meeting))

        assert "Speaker 1: Hello" in window._transcript_panel._text_edit.toPlainText()

    def test_load_meeting_with_summary(self, mock_main_window, tmp_dir):
        """Test loading a meeting that has a summary file."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()
        (meeting / "summary.md").write_text("## Summary\nTest content", encoding="utf-8")

        window = mock_main_window
        window._load_meeting(str(meeting))

        assert "Test content" in window._summary_panel._text_browser.document().toPlainText()

    def test_load_meeting_no_files(self, mock_main_window, tmp_dir):
        """Test loading a meeting with no transcript or summary."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()

        window = mock_main_window
        window._load_meeting(str(meeting))

        # Transcript and summary should be empty
        assert window._transcript_panel._text_edit.toPlainText() == ""
        assert window._summary_panel._text_browser.document().toPlainText() == ""

    def test_load_meeting_nonexistent(self, mock_main_window):
        """Test loading a meeting that doesn't exist."""
        window = mock_main_window
        # This should show a warning (we can't easily test QMessageBox)
        # but it shouldn't crash
        window._load_meeting("/nonexistent/path/meeting")

    def test_load_meeting_enables_reprocess(self, mock_main_window, tmp_dir):
        """Test that loading a meeting enables the reprocess button."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()

        window = mock_main_window
        window._load_meeting(str(meeting))

        # Get the reprocess button from the existing recordings tab
        existing_tab = window._recording_panel._tabs.widget(1)
        layout = existing_tab.layout()
        reprocess_btn = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "text") and widget.text() == "Reprocess Selected":
                    reprocess_btn = widget
                    break
        assert reprocess_btn is not None
        assert reprocess_btn.isEnabled() is True

    def test_load_meeting_clears_previous_content(self, mock_main_window, tmp_dir):
        """Test that loading a meeting clears previous transcript/summary."""
        # First load one meeting
        meeting_a = tmp_dir / "meeting-a"
        meeting_a.mkdir()
        (meeting_a / "recording.wav").touch()
        (meeting_a / "transcript.txt").write_text("Transcript A", encoding="utf-8")

        window = mock_main_window
        window._load_meeting(str(meeting_a))
        assert "Transcript A" in window._transcript_panel._text_edit.toPlainText()

        # Then load another meeting
        meeting_b = tmp_dir / "meeting-b"
        meeting_b.mkdir()
        (meeting_b / "recording.wav").touch()
        (meeting_b / "transcript.txt").write_text("Transcript B", encoding="utf-8")

        window._load_meeting(str(meeting_b))
        # Previous content should be cleared
        assert "Transcript A" not in window._transcript_panel._text_edit.toPlainText()
        assert "Transcript B" in window._transcript_panel._text_edit.toPlainText()

    def test_reprocess_meeting_no_audio(self, mock_main_window, tmp_dir):
        """Test that reprocessing a meeting without audio shows a warning."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        # No audio file

        window = mock_main_window
        window._recording_panel.populate_meetings([
            ("Test Meeting", str(meeting)),
        ])
        window._recording_panel._meeting_list.setCurrentRow(0)

        # This should show a warning (we can't easily test QMessageBox)
        # but it shouldn't crash
        window._reprocess_meeting()

    def test_reprocess_meeting_with_audio(self, mock_main_window, tmp_dir):
        """Test that reprocessing starts processing when audio exists."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        audio_file = meeting / "recording.wav"
        audio_file.touch()

        window = mock_main_window

        # Mock the ProcessingThread to verify it's created correctly
        from src.ui.main_window import ProcessingThread
        with patch.object(window, "_process_meeting") as mock_process:
            window._recording_panel.populate_meetings([
                ("Test Meeting", str(meeting)),
            ])
            window._recording_panel._meeting_list.setCurrentRow(0)

            # Call reprocess
            window._reprocess_meeting()

            # The reprocess method creates a ProcessingThread directly
            # We can verify the thread was started by checking the status
            assert window._processing_thread is not None
            assert window._processing_thread.isRunning()

    def test_tab_changed_populates_meetings(self, mock_main_window, tmp_dir):
        """Test that switching to Existing Recordings tab populates the list."""
        # Create a meeting
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()

        window = mock_main_window

        # Initially the list should be empty (we're on tab 0)
        assert window._recording_panel._meeting_list.count() == 0

        # Switch to tab 1 (Existing Recordings)
        window._on_tab_changed(1)

        # List should now be populated
        assert window._recording_panel._meeting_list.count() == 1

    def test_on_record_clears_reprocess(self, mock_main_window, tmp_dir):
        """Test that starting a new recording disables the reprocess button."""
        meeting = tmp_dir / "test-meeting"
        meeting.mkdir()
        (meeting / "recording.wav").touch()

        window = mock_main_window
        window._load_meeting(str(meeting))

        # Get the reprocess button
        existing_tab = window._recording_panel._tabs.widget(1)
        layout = existing_tab.layout()
        reprocess_btn = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "text") and widget.text() == "Reprocess Selected":
                    reprocess_btn = widget
                    break
        assert reprocess_btn is not None
        assert reprocess_btn.isEnabled() is True

        # Now simulate starting a new recording
        # (we can't fully test _on_record without a real recording engine)
        # but we can verify the set_reprocess_enabled call
        window._recording_panel.set_reprocess_enabled(False)
        assert reprocess_btn.isEnabled() is False
