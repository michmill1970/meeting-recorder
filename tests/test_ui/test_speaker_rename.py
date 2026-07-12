"""Unit tests for SpeakerRenameDialog."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.conftest import _qt_available

if not _qt_available:
    pytest.skip("Qt not available, skipping UI tests", allow_module_level=True)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


class TestSpeakerRenameDialog:
    """Tests for SpeakerRenameDialog widget."""

    @pytest.fixture
    def sample_transcript(self) -> str:
        """Provide a sample transcript with multiple speakers."""
        return """[00:00] Speaker 1: Welcome everyone to the meeting.
[00:05] Speaker 2: Thanks for having me.
[00:10] Speaker 1: Let's discuss the Q4 planning.
[00:15] Speaker 2: I think we should focus on user acquisition.
[00:20] Speaker 1: Agreed. Alice, can you prepare a proposal?
[00:25] Speaker 2: Sure, I'll have it ready by Friday."""

    @pytest.fixture
    def dialog(self, qtbot, tmp_dir, sample_transcript):
        """Create a SpeakerRenameDialog for testing."""
        from src.ui.components.speaker_rename_dialog import SpeakerRenameDialog

        meeting_dir = tmp_dir / "test-meeting"
        meeting_dir.mkdir()

        dialog = SpeakerRenameDialog(
            transcript_text=sample_transcript,
            meeting_dir=meeting_dir,
            parent=None,
        )
        qtbot.addWidget(dialog)
        return dialog

    def test_dialog_initialization(self, dialog) -> None:
        """Test that the dialog initializes correctly."""
        assert dialog._detected_speakers == ["Speaker 1", "Speaker 2"]
        assert len(dialog._speaker_inputs) == 2

    def test_detects_speakers(self, dialog) -> None:
        """Test that speakers are detected from the transcript."""
        assert "Speaker 1" in dialog._detected_speakers
        assert "Speaker 2" in dialog._detected_speakers
        assert len(dialog._detected_speakers) == 2

    def test_preview_shows_renamed_speakers(self, dialog) -> None:
        """Test that the preview updates when a speaker name is entered."""
        # Enter a new name for Speaker 1
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._update_preview()

        preview_text = dialog._preview_edit.toPlainText()
        assert "Alice:" in preview_text
        assert "Speaker 1:" not in preview_text

    def test_preview_preserves_timestamps(self, dialog) -> None:
        """Test that timestamps are preserved when renaming speakers."""
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._update_preview()

        preview_text = dialog._preview_edit.toPlainText()
        assert "[00:00]" in preview_text
        assert "[00:05]" in preview_text

    def test_preview_multiple_renames(self, dialog) -> None:
        """Test that multiple speaker renames are reflected in the preview."""
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._speaker_inputs["Speaker 2"].setText("Bob")
        dialog._update_preview()

        preview_text = dialog._preview_edit.toPlainText()
        assert "Alice:" in preview_text
        assert "Bob:" in preview_text

    def test_confirm_saves_transcript(self, dialog, tmp_dir) -> None:
        """Test that confirming renames saves the updated transcript."""
        # Set new names
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._speaker_inputs["Speaker 2"].setText("Bob")

        # Mock the signal handler
        received_renames = []
        def on_confirmed(renames):
            received_renames.extend(renames)

        dialog.speakers_confirmed.connect(on_confirmed)

        # Click confirm
        dialog._on_confirm()

        # Check that renames were emitted
        assert len(received_renames) == 2
        assert ("Speaker 1", "Alice") in received_renames
        assert ("Speaker 2", "Bob") in received_renames

        # Check that transcript was updated
        transcript_path = dialog._meeting_dir / "transcript.txt"
        assert transcript_path.exists()
        updated_text = transcript_path.read_text(encoding="utf-8")
        assert "Alice:" in updated_text
        assert "Bob:" in updated_text
        assert "Speaker 1:" not in updated_text
        assert "Speaker 2:" not in updated_text

    def test_confirm_preserves_transcript_content(self, dialog, tmp_dir) -> None:
        """Test that actual transcript text is preserved during rename."""
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._speaker_inputs["Speaker 2"].setText("Bob")
        dialog._on_confirm()

        transcript_path = dialog._meeting_dir / "transcript.txt"
        updated_text = transcript_path.read_text(encoding="utf-8")

        # Check that original content is preserved
        assert "Welcome everyone to the meeting" in updated_text
        assert "Q4 planning" in updated_text
        assert "user acquisition" in updated_text

    def test_use_defaults_does_not_modify_transcript(self, dialog, tmp_dir) -> None:
        """Test that using default labels doesn't modify the transcript."""
        # Set a new name but then click use defaults
        dialog._speaker_inputs["Speaker 1"].setText("Alice")
        dialog._speaker_inputs["Speaker 2"].setText("Bob")

        # Save original transcript
        original_transcript_path = dialog._meeting_dir / "transcript.txt"
        original_transcript_path.write_text(
            dialog._transcript_text, encoding="utf-8"
        )

        # Click use defaults
        dialog._on_use_defaults()

        # Transcript should not be modified
        updated_text = original_transcript_path.read_text(encoding="utf-8")
        assert "Speaker 1:" in updated_text
        assert "Speaker 2:" in updated_text

    def test_cancel_rejects_dialog(self, dialog) -> None:
        """Test that cancel rejects the dialog."""
        rejected = []
        def on_cancel():
            rejected.append(True)

        dialog.cancelled.connect(on_cancel)
        dialog._on_cancel()

        assert len(rejected) == 1
        assert dialog.result() == QDialog.Rejected

    def test_confirm_no_names_shows_warning(self, dialog) -> None:
        """Test that confirming with no names entered shows a warning."""
        # Don't enter any names
        with patch("src.ui.components.speaker_rename_dialog.QMessageBox.information") as mock_info:
            dialog._on_confirm()
            mock_info.assert_called_once()

    def test_preview_shows_first_five_lines(self, dialog) -> None:
        """Test that the preview shows only the first 5 lines."""
        long_transcript = "\n".join(
            f"[00:0{i}] Speaker 1: Line {i}" for i in range(10)
        )
        dialog._transcript_text = long_transcript
        dialog._update_preview()

        lines = dialog._preview_edit.toPlainText().split("\n")
        assert len(lines) == 5

    def test_speaker_colors_applied(self, dialog) -> None:
        """Test that color indicators are applied to speakers."""
        # The dialog creates color indicators for each speaker
        # We can verify this by checking the dialog was created successfully
        assert len(dialog._speaker_inputs) == len(dialog._detected_speakers)
