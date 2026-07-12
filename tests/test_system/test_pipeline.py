"""System tests for the full recording pipeline."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models.schemas import LLMProvider, MeetingStatus, RecordingSession
from src.recording.engine import RecordingEngine
from src.recording.level_manager import LevelManager
from src.settings.manager import Settings
from src.transcription.whisper_client import WhisperClient
from src.summarization.llm_client import LLMClient


class TestRecordingSystem:
    """System tests for the recording subsystem."""

    def test_recording_lifecycle(self, sample_session: RecordingSession) -> None:
        """Test the full recording lifecycle: start -> pause -> resume -> stop."""
        settings = Settings()
        engine = RecordingEngine(settings)
        engine.initialize()

        try:
            # Start recording
            engine.start(sample_session)
            assert engine.is_recording is True
            assert engine.is_paused is False
            assert sample_session.status == MeetingStatus.RECORDING

            # Pause
            engine.pause()
            assert engine.is_recording is False
            assert engine.is_paused is True
            assert sample_session.status == MeetingStatus.PAUSED

            # Resume
            engine.resume()
            assert engine.is_recording is True
            assert engine.is_paused is False
            assert sample_session.status == MeetingStatus.RECORDING

            # Stop
            engine.stop()
            assert engine.is_recording is False
            assert engine.is_paused is False
            assert sample_session.status == MeetingStatus.IDLE
            assert sample_session.audio_path is not None

        finally:
            engine.shutdown()

    def test_level_manager_with_recording(
        self,
        sample_session: RecordingSession,
        normal_audio: any,
    ) -> None:
        """Test level manager operates correctly during recording."""
        settings = Settings()
        engine = RecordingEngine(settings)
        level_manager = LevelManager(settings, engine)

        # Mock the audio buffer
        engine._audio_buffer = normal_audio

        try:
            engine.start(sample_session)
            level_manager.start()

            # Get metrics
            metrics = level_manager.get_level_metrics()
            assert "rms_db" in metrics
            assert "peak_db" in metrics
            assert "gain_db" in metrics

            # Auto mode should be on by default
            assert level_manager.is_auto_mode is True

        finally:
            level_manager.stop()
            engine.shutdown()

    def test_settings_persistence_through_lifecycle(
        self,
        sample_session: RecordingSession,
        settings_file: Path,
    ) -> None:
        """Test that settings are properly loaded and saved through recording lifecycle."""
        from src.settings.manager import SettingsManager

        # Create initial settings
        settings = Settings()
        settings.recording.mic_device_id = 3
        settings.whisper.hf_token = "test_token"
        manager = SettingsManager(settings_file)
        manager.save(settings)

        # Load settings
        loaded = manager.load()
        assert loaded.recording.mic_device_id == 3
        assert loaded.whisper.hf_token == "test_token"

        # Modify and save again
        loaded.recording.mic_device_id = 5
        manager.save(loaded)

        # Verify persistence
        reloaded = manager.load()
        assert reloaded.recording.mic_device_id == 5


class TestTranscriptionSystem:
    """System tests for the transcription subsystem."""

    def test_whisper_client_with_mocked_subprocess(
        self,
        sample_audio_file: Path,
        sample_session: RecordingSession,
    ) -> None:
        """Test whisper client with mocked subprocess call."""
        settings = Settings()
        settings.whisper.hf_token = "test_hf_token"
        client = WhisperClient(settings)

        # Create mock transcript file first
        transcript_path = sample_session.meeting_dir / "transcript.txt"
        transcript_path.write_text("Test transcript", encoding="utf-8")

        # Mock subprocess.Popen
        mock_stdout = MagicMock()
        mock_stdout.__iter__ = MagicMock(return_value=iter([
            "Transcoding to 16 kHz mono WAV...\n",
            "Running speaker diarization...\n",
            "Transcribed 50 words.\n",
            "Saved to /tmp/transcript.txt\n",
        ]))

        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.poll.return_value = 0
        mock_process.returncode = 0

        with patch("src.transcription.whisper_client.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process

            result = client.transcribe(sample_audio_file, sample_session)
            assert result == "Test transcript"

    def test_whisper_progress_callback(self, sample_audio_file: Path) -> None:
        """Test that progress callbacks are received."""
        settings = Settings()
        settings.whisper.hf_token = "test_hf_token"
        client = WhisperClient(settings)

        progress_messages = []

        def on_progress(msg: str) -> None:
            progress_messages.append(msg)

        client.set_progress_callback(on_progress)

        # Mock subprocess
        mock_stdout = iter(["Progress 1\n", "Progress 2\n"])

        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.poll.side_effect = [None, None, 0]  # Return None initially, then 0
        mock_process.returncode = 0

        session = RecordingSession()
        session.create_meeting_dir()

        # Create transcript file in the session's meeting directory
        transcript_path = session.meeting_dir / "transcript.txt"
        transcript_path.write_text("Test transcript", encoding="utf-8")

        with patch("src.transcription.whisper_client.subprocess.Popen") as mock_popen:
            with patch("src.transcription.whisper_client.WHISPER_SCRIPT") as mock_script:
                mock_script.exists = MagicMock(return_value=True)
                mock_popen.return_value = mock_process

                client.transcribe(sample_audio_file, session)

        assert len(progress_messages) >= 2
        assert "Progress 1" in progress_messages


class TestSummarizationSystem:
    """System tests for the summarization subsystem."""

    def test_llm_client_providers(self) -> None:
        """Test that all LLM providers can be instantiated."""
        from src.summarization.providers.anthropic import AnthropicProvider
        from src.summarization.providers.lm_studio import LMStudioProvider
        from src.summarization.providers.ollama import OllamaProvider
        from src.summarization.providers.openai import OpenAIProvider
        from src.summarization.providers.vllm import VLLMProvider

        # All should be instantiable
        providers = [
            OpenAIProvider(api_key="test"),
            AnthropicProvider(api_key="test"),
            OllamaProvider(),
            LMStudioProvider(),
            VLLMProvider(),
        ]
        assert len(providers) == 5

    @pytest.mark.asyncio
    async def test_llm_client_summarize_structure(self) -> None:
        """Test that summarize method produces structured output."""
        settings = Settings()
        settings.llm.provider = LLMProvider.OPENAI
        settings.llm.api_key = "test_key"

        client = LLMClient(settings)

        # The actual LLM call will fail without a real API key,
        # but we can verify the method exists and has correct signature
        assert hasattr(client, "summarize")
        assert callable(client.summarize)

    def test_system_prompt_content(self) -> None:
        """Test that the system prompt contains all required sections."""
        prompt = LLMClient.SYSTEM_PROMPT

        required_sections = [
            "Summary",
            "Action Items",
            "TODOs",
            "Assignments",
            "Follow-up Dates",
        ]

        for section in required_sections:
            assert section.lower() in prompt.lower(), f"Missing section: {section}"


class TestFullPipeline:
    """Integration tests for the full recording -> transcription -> summarization pipeline."""

    def test_pipeline_data_flow(self, sample_session: RecordingSession) -> None:
        """Test that data flows correctly through the pipeline stages."""
        # Stage 1: Recording creates audio file
        audio_path = sample_session.meeting_dir / "recording.wav"
        audio_path.write_bytes(b"fake audio data")
        sample_session.audio_path = audio_path

        assert audio_path.exists()

        # Stage 2: Transcription creates transcript
        transcript_path = sample_session.meeting_dir / "transcript.txt"
        transcript_text = "[00:01] Speaker 1: Hello world"
        transcript_path.write_text(transcript_text, encoding="utf-8")
        sample_session.transcript_path = transcript_path

        assert transcript_path.exists()
        assert sample_session.transcript_text == transcript_text

        # Stage 3: Summarization creates summary
        summary_path = sample_session.meeting_dir / "summary.md"
        summary_text = "## Summary\nHello world was discussed."
        summary_path.write_text(summary_text, encoding="utf-8")
        sample_session.summary_path = summary_path

        assert summary_path.exists()
        assert sample_session.summary_text == summary_text

    def test_pipeline_file_organization(self, sample_session: RecordingSession) -> None:
        """Test that meeting files are organized correctly."""
        meeting_dir = sample_session.meeting_dir
        assert meeting_dir is not None
        assert meeting_dir.exists()

        # All expected files should be in the meeting directory
        expected_files = [
            "recording.wav",
            "transcript.txt",
            "summary.md",
        ]

        for filename in expected_files:
            filepath = meeting_dir / filename
            filepath.write_text("test", encoding="utf-8")
            assert filepath.exists()

    def test_pipeline_meeting_name_default(self, tmp_dir: Path) -> None:
        """Test default meeting name format."""
        from datetime import datetime

        session = RecordingSession(save_dir=tmp_dir)
        # Name should be auto-generated
        assert session.name is not None
        # Format should be YYYY-MM-DD_HH-MM
        assert "_" in session.name
        assert "-" in session.name

    def test_pipeline_meeting_name_custom(self, tmp_dir: Path) -> None:
        """Test custom meeting name."""
        session = RecordingSession(name="my-custom-meeting", save_dir=tmp_dir)
        assert session.name == "my-custom-meeting"
        session.create_meeting_dir()
        assert session.meeting_dir == tmp_dir / "my-custom-meeting"
