"""Data models for the meeting recorder application."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class MeetingStatus(Enum):
    """Current status of a meeting recording session."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PROCESSING = "processing"
    DONE = "done"


class RecordingSession:
    """Represents a single meeting recording session."""

    def __init__(
        self,
        name: Optional[str] = None,
        save_dir: Path | None = None,
    ):
        self.name = name or datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.save_dir = save_dir or Path.home() / "Documents" / "MeetingRecorder"
        self.meeting_dir: Optional[Path] = None
        self.audio_path: Optional[Path] = None
        self.transcript_path: Optional[Path] = None
        self.summary_path: Optional[Path] = None
        self.status = MeetingStatus.IDLE
        self.start_time: Optional[datetime] = None
        self.pause_start_time: Optional[datetime] = None
        self.total_pause_duration: float = 0.0
        self.elapsed_time: float = 0.0

    def create_meeting_dir(self) -> Path:
        """Create the meeting directory structure."""
        self.meeting_dir = self.save_dir / self.name
        self.meeting_dir.mkdir(parents=True, exist_ok=True)
        return self.meeting_dir

    @property
    def elapsed_formatted(self) -> str:
        """Format elapsed time as MM:SS or HH:MM:SS."""
        if self.elapsed_time <= 0:
            return "00:00"
        hours = int(self.elapsed_time // 3600)
        minutes = int((self.elapsed_time % 3600) // 60)
        seconds = int(self.elapsed_time % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def transcript_text(self) -> str:
        """Read transcript file if it exists."""
        if self.transcript_path and self.transcript_path.exists():
            return self.transcript_path.read_text(encoding="utf-8")
        return ""

    @property
    def summary_text(self) -> str:
        """Read summary file if it exists."""
        if self.summary_path and self.summary_path.exists():
            return self.summary_path.read_text(encoding="utf-8")
        return ""


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    VLLM = "vllm"

    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        return self in (LLMProvider.OPENAI, LLMProvider.ANTHROPIC)

    @property
    def default_base_url(self) -> str:
        """Return default base URL for this provider."""
        urls = {
            LLMProvider.OLLAMA: "http://localhost:11434",
            LLMProvider.LM_STUDIO: "http://localhost:1234/v1",
            LLMProvider.VLLM: "http://localhost:8000/v1",
        }
        return urls.get(self, "")

    @property
    def api_path(self) -> str:
        """Return the API endpoint path."""
        if self in (LLMProvider.OLLAMA,):
            return "/api/generate"
        return "/chat/completions"


class SummarizationStyle(str, Enum):
    """Summarization verbosity style."""
    CONCISE = "concise"
    NORMAL = "normal"
    DETAILED = "detailed"
    CUSTOM = "custom"

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            SummarizationStyle.CONCISE: "Concise",
            SummarizationStyle.NORMAL: "Normal",
            SummarizationStyle.DETAILED: "Detailed",
            SummarizationStyle.CUSTOM: "Custom",
        }.get(self, self.value)


class WhisperSpeakerMode(str, Enum):
    """How to specify speaker count for Whisper diarization."""
    AUTO = "auto"
    SPECIFIC = "specific"
    RANGE = "range"


class AudioFormat(str, Enum):
    """Audio recording format. All formats are supported by Whisper via ffmpeg."""

    WAV = "wav"
    FLAC = "flac"
    OPUS = "opus"
    MP3 = "mp3"
    OGG = "ogg"

    @property
    def label(self) -> str:
        """Human-readable label for the format."""
        labels = {
            AudioFormat.WAV: "WAV (Uncompressed)",
            AudioFormat.FLAC: "FLAC (Lossless)",
            AudioFormat.OPUS: "OPUS (Recommended)",
            AudioFormat.MP3: "MP3 (Universal)",
            AudioFormat.OGG: "OGG Vorbis",
        }
        return labels.get(self, self.value.upper())

    @property
    def hint(self) -> str:
        """Help text describing the format's characteristics."""
        hints = {
            AudioFormat.WAV: "Largest file size, no quality loss. Best for archival.",
            AudioFormat.FLAC: "Lossless compression. ~40-60% smaller than WAV with no quality loss.",
            AudioFormat.OPUS: "Best quality/size ratio. ~10x smaller than WAV. Recommended for most use cases.",
            AudioFormat.MP3: "Universal compatibility. Good quality at ~15x smaller than WAV.",
            AudioFormat.OGG: "Open-source alternative to MP3. Good quality at ~12x smaller than WAV.",
        }
        return hints.get(self, "")

    @property
    def extension(self) -> str:
        """File extension for the format."""
        return self.value
