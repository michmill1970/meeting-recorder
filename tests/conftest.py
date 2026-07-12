"""Pytest configuration and shared fixtures for the meeting recorder test suite."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Mock pyaudio before any imports that might use it
sys.modules["pyaudio"] = MagicMock()

# Mock PySide6 GUI modules for headless test environments
# Only mock if PySide6 is not available or Qt can't be initialized
_pyside6_available = True
_qt_available = True
try:
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtWidgets import QWidget
except (ImportError, OSError) as e:
    _pyside6_available = False
    _qt_available = False
    # Mock modules if import fails
    if "PySide6.QtGui" not in sys.modules:
        sys.modules["PySide6.QtGui"] = MagicMock()
    if "PySide6.QtCore" not in sys.modules:
        sys.modules["PySide6.QtCore"] = MagicMock()
    if "PySide6.QtWidgets" not in sys.modules:
        sys.modules["PySide6.QtWidgets"] = MagicMock()

from src.models.schemas import LLMProvider, MeetingStatus, RecordingSession, WhisperSpeakerMode
from src.settings.manager import Settings, SettingsManager


# ============================================================================
# Temporary directory fixtures
# ============================================================================

@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def settings_file(tmp_dir: Path) -> Path:
    """Provide a temporary settings file path."""
    return tmp_dir / "settings.json"


@pytest.fixture
def sample_audio_file(tmp_dir: Path) -> Path:
    """Create a sample WAV file for testing."""
    import wave

    audio_path = tmp_dir / "test_audio.wav"
    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # Generate 1 second of silent audio
        samples = np.zeros(16000, dtype=np.int16)
        wf.writeframes(samples.tobytes())
    return audio_path


@pytest.fixture
def sample_transcript(tmp_dir: Path) -> Path:
    """Create a sample transcript file for testing."""
    transcript_path = tmp_dir / "transcript.txt"
    transcript_text = """[00:01] Speaker 1: Welcome everyone to the meeting.
[00:05] Speaker 2: Thanks for having me.
[00:10] Speaker 1: Let's discuss the Q4 planning.
[00:15] Speaker 2: I think we should focus on user acquisition.
[00:20] Speaker 1: Agreed. Alice, can you prepare a proposal?
[00:25] Speaker 2: Sure, I'll have it ready by Friday."""
    transcript_path.write_text(transcript_text, encoding="utf-8")
    return transcript_path


@pytest.fixture
def sample_summary(tmp_dir: Path) -> Path:
    """Create a sample summary file for testing."""
    summary_path = tmp_dir / "summary.md"
    summary_text = """## Summary
The team discussed Q4 planning and agreed to focus on user acquisition.

## Action Items
- Alice: Prepare user acquisition proposal by Friday

## Follow-up Dates
- Proposal due: Friday"""
    summary_path.write_text(summary_text, encoding="utf-8")
    return summary_path


# ============================================================================
# Settings fixtures
# ============================================================================

@pytest.fixture
def default_settings() -> Settings:
    """Provide default settings instance."""
    return Settings()


@pytest.fixture
def sample_settings(settings_file: Path) -> Settings:
    """Provide settings with sample values."""
    settings = Settings()
    settings.recording.save_dir = str(settings_file.parent / "Meetings")
    settings.whisper.hf_token = "test_hf_token_12345"
    settings.llm.api_key = "test_api_key_67890"
    settings.llm.model = "gpt-4o"
    # Save to disk
    manager = SettingsManager(settings_file)
    manager.save(settings)
    return settings


@pytest.fixture
def settings_manager(settings_file: Path) -> SettingsManager:
    """Provide a SettingsManager instance with custom file path."""
    return SettingsManager(settings_file)


# ============================================================================
# RecordingSession fixtures
# ============================================================================

@pytest.fixture
def sample_session(tmp_dir: Path) -> RecordingSession:
    """Provide a RecordingSession with test directory."""
    session = RecordingSession(
        name="test-meeting",
        save_dir=tmp_dir,
    )
    session.create_meeting_dir()
    return session


# ============================================================================
# Mock fixtures
# ============================================================================

@pytest.fixture
def mock_pyaudio() -> MagicMock:
    """Provide a mocked PyAudio instance."""
    mock = MagicMock()
    mock.get_device_count.return_value = 2
    mock.get_device_info_by_index.side_effect = [
        {
            "name": "Test Microphone",
            "defaultSampleRate": 16000.0,
            "maxInputChannels": 1,
        },
        {
            "name": "System Default",
            "defaultSampleRate": 44100.0,
            "maxInputChannels": 2,
        },
    ]
    return mock


@pytest.fixture
def mock_settings_manager(settings_file: Path) -> SettingsManager:
    """Provide a SettingsManager for testing."""
    return SettingsManager(settings_file)


@pytest.fixture
def sample_labeled_words() -> list[dict]:
    """Provide sample word-level transcription with speaker labels."""
    return [
        {"start": 0.0, "end": 0.5, "text": "Hello", "speaker": "SPEAKER_00"},
        {"start": 0.5, "end": 1.0, "text": "world", "speaker": "SPEAKER_00"},
        {"start": 1.5, "end": 2.0, "text": "Hi", "speaker": "SPEAKER_01"},
        {"start": 2.0, "end": 2.5, "text": "there", "speaker": "SPEAKER_01"},
    ]


@pytest.fixture
def sample_diarization_intervals() -> list[dict]:
    """Provide sample diarization intervals."""
    return [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"start": 1.5, "end": 3.0, "speaker": "SPEAKER_01"},
    ]


# ============================================================================
# Audio fixtures
# ============================================================================

@pytest.fixture
def silent_audio() -> np.ndarray:
    """Provide silent audio samples."""
    return np.zeros(1600, dtype=np.int16)


@pytest.fixture
def quiet_audio() -> np.ndarray:
    """Provide quiet audio samples (low amplitude)."""
    return np.random.randint(-100, 100, size=1600, dtype=np.int16)


@pytest.fixture
def loud_audio() -> np.ndarray:
    """Provide loud audio samples (high amplitude)."""
    return np.random.randint(-10000, 10000, size=1600, dtype=np.int16)


@pytest.fixture
def normal_audio() -> np.ndarray:
    """Provide normal speech-level audio samples."""
    return np.random.randint(-5000, 5000, size=1600, dtype=np.int16)


# ============================================================================
# Temporary settings directory fixture
# ============================================================================

@pytest.fixture
def temp_settings_dir(tmp_dir: Path) -> Generator[Path, None, None]:
    """Provide a temporary settings directory, restoring after test."""
    original = Path.home() / ".config" / "meeting-recorder"
    backup = None
    if original.exists():
        backup = tmp_dir / "settings_backup"
        shutil.copytree(original, backup)

    yield tmp_dir

    # Restore original if it existed
    if backup and original.exists():
        shutil.rmtree(original, ignore_errors=True)
        shutil.copytree(backup, original)


# ============================================================================
# Qt availability fixture for UI tests
# ============================================================================

@pytest.fixture
def qt_available() -> bool:
    """Check if Qt is available for UI tests."""
    return _qt_available


# ============================================================================
# QApplication autouse fixture for UI component tests
# ============================================================================

@pytest.fixture(autouse=True)
def _ensure_qapp():
    """Ensure a QApplication exists for any test that imports Qt widgets."""
    if _qt_available:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
            yield app
        else:
            yield QApplication.instance()
    else:
        yield
