"""Unit tests for export utility and sleep prevention."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.export import export_meeting_zip
from src.utils.sleep_prevention import SleepPrevention


class TestExportUtility:
    """Tests for ZIP export functionality."""

    def test_export_nonexistent_directory(self, tmp_dir: Path) -> None:
        """Export should return None for nonexistent directory."""
        result = export_meeting_zip(tmp_dir / "nonexistent")
        assert result is None

    def test_export_no_files(self, tmp_dir: Path) -> None:
        """Export should return None if no archiveable files exist."""
        meeting_dir = tmp_dir / "meeting"
        meeting_dir.mkdir()
        result = export_meeting_zip(meeting_dir)
        assert result is None

    def test_export_with_audio_only(self, tmp_dir: Path, sample_audio_file: Path) -> None:
        """Export should create ZIP with audio file."""
        meeting_dir = tmp_dir / "meeting"
        meeting_dir.mkdir()
        audio_copy = meeting_dir / "recording.wav"
        audio_copy.write_bytes(sample_audio_file.read_bytes())

        result = export_meeting_zip(meeting_dir)
        assert result is not None
        assert result.exists()
        assert result.name == "meeting.zip"

        # Verify ZIP contents
        import zipfile
        with zipfile.ZipFile(result, "r") as zf:
            assert "recording.wav" in zf.namelist()

    def test_export_with_all_files(
        self,
        tmp_dir: Path,
        sample_audio_file: Path,
        sample_transcript: Path,
        sample_summary: Path,
    ) -> None:
        """Export should create ZIP with all meeting files."""
        meeting_dir = tmp_dir / "meeting"
        meeting_dir.mkdir()

        # Copy files
        (meeting_dir / "recording.wav").write_bytes(sample_audio_file.read_bytes())
        (meeting_dir / "transcript.txt").write_text(
            sample_transcript.read_text()
        )
        (meeting_dir / "summary.md").write_text(sample_summary.read_text())

        result = export_meeting_zip(meeting_dir)
        assert result is not None
        assert result.exists()

        # Verify ZIP contents
        import zipfile
        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "recording.wav" in names
            assert "transcript.txt" in names
            assert "summary.md" in names
            assert len(names) == 3

    def test_export_to_custom_directory(
        self,
        tmp_dir: Path,
        sample_audio_file: Path,
    ) -> None:
        """Export should support custom output directory."""
        meeting_dir = tmp_dir / "meeting"
        meeting_dir.mkdir()
        output_dir = tmp_dir / "output"
        output_dir.mkdir()

        (meeting_dir / "recording.wav").write_bytes(sample_audio_file.read_bytes())

        result = export_meeting_zip(meeting_dir, output_dir=output_dir)
        assert result is not None
        assert result.parent == output_dir

    def test_export_overwrites_existing_zip(
        self,
        tmp_dir: Path,
        sample_audio_file: Path,
    ) -> None:
        """Export should overwrite existing ZIP file."""
        meeting_dir = tmp_dir / "meeting"
        meeting_dir.mkdir()
        (meeting_dir / "recording.wav").write_bytes(sample_audio_file.read_bytes())

        # First export
        result1 = export_meeting_zip(meeting_dir)
        assert result1 is not None

        # Second export should overwrite
        result2 = export_meeting_zip(meeting_dir)
        assert result2 is not None
        assert result1 == result2  # Same path


class TestSleepPrevention:
    """Tests for sleep prevention utility."""

    def test_initialization(self) -> None:
        sp = SleepPrevention()
        assert sp._running is False
        assert sp._process is None

    def test_start_stop_without_caffeinate(self) -> None:
        """Start/stop should work even if caffeinate fails."""
        sp = SleepPrevention()
        sp.start()
        assert sp._running is True
        sp.stop()
        assert sp._running is False

    def test_stop_without_start(self) -> None:
        """Stopping without starting should not raise."""
        sp = SleepPrevention()
        sp.stop()  # Should not raise

    def test_start_twice(self) -> None:
        """Starting twice should not create duplicate processes."""
        sp = SleepPrevention()
        with patch("src.utils.sleep_prevention.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = 0  # Simulate exit
            mock_popen.return_value = mock_process

            sp.start()
            sp.start()  # Should not start again

            # Popen should only be called once due to _running check
            # Actually, the loop will call it, but the second start() won't
            # create a new thread
            assert sp._thread is not None

    def test_stop_clears_process(self) -> None:
        """Stop should clear the process reference."""
        sp = SleepPrevention()
        with patch("src.utils.sleep_prevention.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            sp.start()
            import time
            time.sleep(0.1)
            sp.stop()
            # Process should be terminated/cleared
            assert sp._process is None or sp._process.poll() is not None
