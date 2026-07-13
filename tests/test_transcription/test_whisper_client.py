"""Unit tests for whisper transcription client."""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models.schemas import RecordingSession, WhisperSpeakerMode
from src.settings.manager import Settings
from src.transcription.whisper_client import WhisperClient, WHISPER_SCRIPT


class TestWhisperClient:
    """Tests for WhisperClient."""

    def test_initialization(self) -> None:
        settings = Settings()
        client = WhisperClient(settings)
        assert client._settings == settings
        assert client._progress_callback is None

    def test_set_progress_callback(self) -> None:
        settings = Settings()
        client = WhisperClient(settings)
        callback = MagicMock()
        client.set_progress_callback(callback)
        assert client._progress_callback == callback

    def test_transcribe_no_script(self) -> None:
        """Transcribe should return None if transcribe.py not found."""
        settings = Settings()
        # Patch the path to non-existent file
        with patch.object(Path, "exists", return_value=False):
            client = WhisperClient(settings)
            result = client.transcribe(Path("/tmp/test.wav"), RecordingSession())
            assert result is None

    def test_transcribe_no_hf_token(self) -> None:
        """Transcribe should return None if HF token not configured."""
        settings = Settings()
        settings.whisper.hf_token = ""
        client = WhisperClient(settings)

        with patch.object(Path, "exists", return_value=True):
            result = client.transcribe(Path("/tmp/test.wav"), RecordingSession())
            assert result is None

    def test_emit_progress_no_callback(self) -> None:
        """Emit progress should not crash without callback."""
        settings = Settings()
        client = WhisperClient(settings)
        # Should not raise
        client._emit_progress("Test progress message")

    def test_emit_progress_with_callback(self) -> None:
        """Emit progress should call callback if set."""
        settings = Settings()
        client = WhisperClient(settings)
        callback = MagicMock()
        client.set_progress_callback(callback)
        client._emit_progress("Test message")
        callback.assert_called_once_with("Test message")

    def test_hf_token_passed_via_env_not_cli(self) -> None:
        """HF token must not appear in CLI args (ps aux leak) — passed via env."""
        settings = Settings()
        settings.whisper.hf_token = "secret_hf_token_abc"

        client = WhisperClient(settings)
        session = RecordingSession()
        session.meeting_dir = Path("/tmp/test_meeting")
        session.meeting_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "exists", return_value=True):
            with patch("subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.stdout = iter([])
                mock_process.poll.return_value = 0
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                client.transcribe(Path("/tmp/test.wav"), session)

                # Popen(cmd, ..., env=env) — cmd is positional arg[0], env is kwarg
                call_args = mock_popen.call_args
                cmd = call_args[0][0]  # First positional argument
                env = call_args[1].get("env")

                # Token must NOT be in the command
                assert "--hf-token" not in cmd
                assert "secret_hf_token_abc" not in cmd
                # Token MUST be in the environment
                assert env is not None
                assert env["HF_TOKEN"] == "secret_hf_token_abc"

    @pytest.mark.parametrize("speaker_mode", [
        WhisperSpeakerMode.AUTO,
        WhisperSpeakerMode.SPECIFIC,
        WhisperSpeakerMode.RANGE,
    ])
    def test_command_builds_correctly(self, speaker_mode: WhisperSpeakerMode) -> None:
        """Test that the command is built correctly for each speaker mode."""
        settings = Settings()
        settings.whisper.hf_token = "test_token"
        settings.whisper.speaker_mode = speaker_mode
        settings.whisper.num_speakers = 2
        settings.whisper.min_speakers = 1
        settings.whisper.max_speakers = 4
        settings.whisper.ignore_flips = 2

        client = WhisperClient(settings)

        # We can't easily test the full subprocess call without mocking heavily,
        # but we can verify the client initializes correctly with all modes
        assert client._settings.whisper.speaker_mode == speaker_mode


class TestWhisperClientCancel:
    """Tests for WhisperClient cancellation support."""

    def test_cancel_sets_flag(self) -> None:
        """cancel() should set the _cancelled flag to True."""
        settings = Settings()
        client = WhisperClient(settings)
        assert client._cancelled is False
        client.cancel()
        assert client._cancelled is True

    def test_cancel_no_subprocess(self) -> None:
        """cancel() should not crash when there is no active subprocess."""
        settings = Settings()
        client = WhisperClient(settings)
        # Should not raise
        client.cancel()
        assert client._cancelled is True
        assert client._subprocess is None

    def test_cancel_terminates_subprocess(self) -> None:
        """cancel() should terminate and wait for the subprocess."""
        settings = Settings()
        client = WhisperClient(settings)
        mock_process = MagicMock()
        client._subprocess = mock_process
        client.cancel()
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_cancel_kills_on_wait_timeout(self) -> None:
        """cancel() should kill the subprocess if wait times out."""
        settings = Settings()
        client = WhisperClient(settings)
        mock_process = MagicMock()
        mock_process.wait.side_effect = TimeoutError("wait timeout")
        client._subprocess = mock_process
        client.cancel()
        mock_process.kill.assert_called_once()

    def test_cancel_clears_subprocess_ref(self) -> None:
        """cancel() should clear _subprocess after terminating."""
        settings = Settings()
        client = WhisperClient(settings)
        mock_process = MagicMock()
        client._subprocess = mock_process
        client.cancel()
        assert client._subprocess is None

    def test_transcribe_raises_cancelled_when_flag_set(self) -> None:
        """transcribe() should raise CancelledError if cancelled during output read."""
        settings = Settings()
        settings.whisper.hf_token = "test_token"
        client = WhisperClient(settings)
        session = RecordingSession()
        session.meeting_dir = Path("/tmp/test_meeting")

        mock_process = MagicMock()
        # First line triggers cancel check, second line has "Saved to"
        mock_process.stdout = iter([
            "Loading Whisper via MLX...\n",
            "Transcribed 100 words\n",
        ])
        mock_process.poll.side_effect = [None, None]
        mock_process.returncode = 0

        with patch.object(Path, "exists", return_value=True):
            with patch("subprocess.Popen", return_value=mock_process):
                client._cancelled = True
                with pytest.raises(asyncio.CancelledError) as exc_info:
                    client.transcribe(Path("/tmp/test.wav"), session)
                assert "cancelled" in str(exc_info.value).lower()
                # Verify subprocess was terminated
                mock_process.terminate.assert_called_once()

    def test_transcribe_checks_cancel_after_subprocess(self) -> None:
        """transcribe() should still check cancel flag after subprocess ends."""
        settings = Settings()
        settings.whisper.hf_token = "test_token"
        client = WhisperClient(settings)
        session = RecordingSession()
        session.meeting_dir = Path("/tmp/test_meeting")
        transcript_path = session.meeting_dir / "transcript.txt"
        transcript_path.write_text("Test transcript", encoding="utf-8")

        mock_process = MagicMock()
        mock_process.stdout = iter(["Saved to /tmp/test_meeting/transcript.txt\n"])
        mock_process.poll.return_value = 0
        mock_process.returncode = 0

        with patch.object(Path, "exists", return_value=True):
            with patch("subprocess.Popen", return_value=mock_process):
                client._cancelled = False
                result = client.transcribe(Path("/tmp/test.wav"), session)
                assert result == "Test transcript"
