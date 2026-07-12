"""Unit tests for data models and schemas."""

from datetime import datetime
from pathlib import Path

import pytest

from src.models.schemas import (
    LLMProvider,
    MeetingStatus,
    RecordingSession,
    WhisperSpeakerMode,
)


class TestMeetingStatus:
    """Tests for MeetingStatus enum."""

    def test_meeting_status_values(self) -> None:
        assert MeetingStatus.IDLE.value == "idle"
        assert MeetingStatus.RECORDING.value == "recording"
        assert MeetingStatus.PAUSED.value == "paused"
        assert MeetingStatus.PROCESSING.value == "processing"
        assert MeetingStatus.DONE.value == "done"

    def test_meeting_status_identity(self) -> None:
        assert MeetingStatus.IDLE != MeetingStatus.RECORDING
        assert MeetingStatus.PAUSED == MeetingStatus.PAUSED


class TestRecordingSession:
    """Tests for RecordingSession model."""

    def test_default_initialization(self) -> None:
        session = RecordingSession()
        assert session.name is not None
        assert session.save_dir == Path.home() / "Documents" / "MeetingRecorder"
        assert session.meeting_dir is None
        assert session.audio_path is None
        assert session.transcript_path is None
        assert session.summary_path is None
        assert session.status == MeetingStatus.IDLE
        assert session.start_time is None
        assert session.pause_start_time is None
        assert session.total_pause_duration == 0.0
        assert session.elapsed_time == 0.0

    def test_custom_initialization(self, tmp_dir: Path) -> None:
        session = RecordingSession(
            name="my-meeting",
            save_dir=tmp_dir,
        )
        assert session.name == "my-meeting"
        assert session.save_dir == tmp_dir

    def test_create_meeting_dir(self, tmp_dir: Path) -> None:
        session = RecordingSession(save_dir=tmp_dir)
        meeting_dir = session.create_meeting_dir()

        assert meeting_dir is not None
        assert meeting_dir.exists()
        assert meeting_dir == tmp_dir / session.name

    def test_elapsed_formatted_zero(self) -> None:
        session = RecordingSession()
        session.elapsed_time = 0
        assert session.elapsed_formatted == "00:00"

    def test_elapsed_formatted_minutes_seconds(self) -> None:
        session = RecordingSession()
        session.elapsed_time = 125.5  # 2 minutes, 5 seconds
        assert session.elapsed_formatted == "02:05"

    def test_elapsed_formatted_hours(self) -> None:
        session = RecordingSession()
        session.elapsed_time = 3661.0  # 1 hour, 1 minute, 1 second
        assert session.elapsed_formatted == "01:01:01"

    def test_elapsed_formatted_single_digit(self) -> None:
        session = RecordingSession()
        session.elapsed_time = 45.0
        assert session.elapsed_formatted == "00:45"

    def test_transcript_text_missing_file(self) -> None:
        session = RecordingSession()
        assert session.transcript_text == ""

    def test_transcript_text_present_file(self, tmp_dir: Path, sample_transcript: Path) -> None:
        session = RecordingSession(save_dir=tmp_dir)
        session.transcript_path = sample_transcript
        assert session.transcript_text == sample_transcript.read_text()

    def test_summary_text_missing_file(self) -> None:
        session = RecordingSession()
        assert session.summary_text == ""

    def test_summary_text_present_file(self, tmp_dir: Path, sample_summary: Path) -> None:
        session = RecordingSession(save_dir=tmp_dir)
        session.summary_path = sample_summary
        assert session.summary_text == sample_summary.read_text()

    def test_pause_tracking(self) -> None:
        session = RecordingSession()
        session.pause_start_time = datetime(2025, 1, 1, 12, 0, 0)
        session.total_pause_duration = 10.0

        # Simulate pause end
        end_time = datetime(2025, 1, 1, 12, 0, 15)
        pause_duration = (end_time - session.pause_start_time).total_seconds()
        session.total_pause_duration += pause_duration
        session.pause_start_time = None

        assert session.total_pause_duration == 25.0
        assert session.pause_start_time is None


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self) -> None:
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OLLAMA.value == "ollama"
        assert LLMProvider.LM_STUDIO.value == "lm_studio"
        assert LLMProvider.VLLM.value == "vllm"

    def test_requires_api_key(self) -> None:
        assert LLMProvider.OPENAI.requires_api_key is True
        assert LLMProvider.ANTHROPIC.requires_api_key is True
        assert LLMProvider.OLLAMA.requires_api_key is False
        assert LLMProvider.LM_STUDIO.requires_api_key is False
        assert LLMProvider.VLLM.requires_api_key is False

    def test_default_base_url(self) -> None:
        assert LLMProvider.OLLAMA.default_base_url == "http://localhost:11434"
        assert LLMProvider.LM_STUDIO.default_base_url == "http://localhost:1234/v1"
        assert LLMProvider.VLLM.default_base_url == "http://localhost:8000/v1"
        assert LLMProvider.OPENAI.default_base_url == ""
        assert LLMProvider.ANTHROPIC.default_base_url == ""

    def test_api_path(self) -> None:
        assert LLMProvider.OLLAMA.api_path == "/api/generate"
        assert LLMProvider.OPENAI.api_path == "/chat/completions"
        assert LLMProvider.ANTHROPIC.api_path == "/chat/completions"


class TestWhisperSpeakerMode:
    """Tests for WhisperSpeakerMode enum."""

    def test_speaker_mode_values(self) -> None:
        assert WhisperSpeakerMode.AUTO.value == "auto"
        assert WhisperSpeakerMode.SPECIFIC.value == "specific"
        assert WhisperSpeakerMode.RANGE.value == "range"

    def test_speaker_mode_equality(self) -> None:
        assert WhisperSpeakerMode.AUTO != WhisperSpeakerMode.SPECIFIC
        assert WhisperSpeakerMode.RANGE == WhisperSpeakerMode.RANGE
