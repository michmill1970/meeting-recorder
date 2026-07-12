"""Settings management for the meeting recorder application.

Handles loading, saving, and validation of application settings
stored in a JSON file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.schemas import (
    AudioFormat,
    LLMProvider,
    SummarizationStyle,
    WhisperSpeakerMode,
)

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SAVE_DIR = str(Path.home() / "Documents" / "MeetingRecorder")


class RecordingSettings(BaseModel):
    """Settings for audio recording."""

    mic_device_id: int = 0
    save_dir: str = DEFAULT_SAVE_DIR
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    audio_format: AudioFormat = AudioFormat.WAV


class AudioLevelingSettings(BaseModel):
    """Settings for automatic audio level adjustment."""

    auto_mode: bool = True
    # Target RMS level relative to noise floor (dB)
    rms_target_db: float = -20.0
    # Threshold = noise_floor + noise_floor_offset_db
    noise_floor_offset_db: float = 10.0
    # Silence duration before considering it "dead air" (seconds)
    dead_air_timeout_sec: float = 60.0
    # Maximum gain adjustment range (dB)
    max_gain_db: float = 12.0
    # Maximum rate of gain change (dB per second)
    gain_ramp_rate_db_per_sec: float = 0.5
    # Duration for ambient noise calibration at start of recording (seconds)
    calibration_duration_sec: float = 5.0


class WhisperSettings(BaseModel):
    """Settings for Whisper transcription."""

    hf_token: str = ""
    speaker_mode: WhisperSpeakerMode = WhisperSpeakerMode.AUTO
    num_speakers: Optional[int] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    ignore_flips: int = 2


class LLMGenerationSettings(BaseModel):
    """Advanced LLM generation parameters.

    These control how the LLM produces text — temperature, sampling,
    repetition, and diversity knobs. Grouped into presets for quick selection.
    """

    # Sampling
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40

    # Repetition
    repetition_penalty: float = 1.1

    # Diversity
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

    # Preset (for quick selection)
    preset: str = "balanced"

    @property
    def preset_description(self) -> str:
        """Return a description of the current preset's intent."""
        return {
            "focused": "Low creativity, highly consistent output. Best for factual summaries.",
            "balanced": "A good mix of creativity and consistency. Default for most use cases.",
            "creative": "Higher variety and unexpected phrasing. Best for brainstorming.",
        }.get(self.preset, "Custom configuration.")

    def to_dict(self) -> dict:
        """Return generation parameters as a dict suitable for API calls."""
        params: dict = {
            "temperature": self.temperature,
            "max_tokens": 4096,
        }
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.top_k is not None:
            params["top_k"] = self.top_k
        if self.repetition_penalty is not None and self.repetition_penalty != 1.0:
            params["repetition_penalty"] = self.repetition_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        return params

    @classmethod
    def presets(cls) -> list[str]:
        """Return list of available preset names."""
        return ["focused", "balanced", "creative"]

    @classmethod
    def from_preset(cls, preset: str) -> LLMGenerationSettings:
        """Create generation settings from a preset name."""
        defaults = {
            "focused": {
                "temperature": 0.1,
                "top_p": 0.5,
                "top_k": 20,
                "repetition_penalty": 1.2,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
            },
            "balanced": {
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "repetition_penalty": 1.1,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
            },
            "creative": {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 64,
                "repetition_penalty": 1.05,
                "presence_penalty": 0.3,
                "frequency_penalty": 0.3,
            },
        }
        values = defaults.get(preset, defaults["balanced"])
        values["preset"] = preset
        return cls(**values)


class LLMSettings(BaseModel):
    """Settings for LLM summarization."""

    provider: LLMProvider = LLMProvider.OPENAI
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o"
    summarization_style: SummarizationStyle = SummarizationStyle.NORMAL
    custom_prompt: str = ""
    use_chat_api: bool = True
    generation: LLMGenerationSettings = Field(default_factory=LLMGenerationSettings)


class Settings(BaseModel):
    """Top-level application settings."""

    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    audio_leveling: AudioLevelingSettings = Field(default_factory=AudioLevelingSettings)
    whisper: WhisperSettings = Field(default_factory=WhisperSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    def model_dump_filtered(self) -> dict[str, Any]:
        """Dump settings, excluding empty sensitive fields."""
        data = self.model_dump()
        # Don't persist empty API keys
        if not data.get("llm", {}).get("api_key"):
            data.setdefault("llm", {})["api_key"] = ""
        if not data.get("whisper", {}).get("hf_token"):
            data.setdefault("whisper", {})["hf_token"] = ""
        return data


class SettingsManager:
    """Manages persistence and loading of application settings."""

    SETTINGS_DIR = Path.home() / ".config" / "meeting-recorder"
    SETTINGS_FILE = SETTINGS_DIR / "settings.json"

    def __init__(self, settings_file: Optional[Path] = None):
        if settings_file is not None:
            self.SETTINGS_FILE = settings_file
            self.SETTINGS_DIR = settings_file.parent

    def load(self) -> Settings:
        """Load settings from JSON file. Returns default settings if file doesn't exist."""
        if not self.SETTINGS_FILE.exists():
            logger.info("No settings file found, using defaults")
            return Settings()

        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Convert string enum values back to enum instances
            recording = raw.get("recording", {})
            if isinstance(recording.get("audio_format"), str):
                recording["audio_format"] = AudioFormat(recording["audio_format"])
            raw["recording"] = recording

            whisper = raw.get("whisper", {})
            if isinstance(whisper.get("speaker_mode"), str):
                whisper["speaker_mode"] = WhisperSpeakerMode(whisper["speaker_mode"])
            raw["whisper"] = whisper

            llm = raw.get("llm", {})
            if isinstance(llm.get("provider"), str):
                llm["provider"] = LLMProvider(llm["provider"])
            if isinstance(llm.get("summarization_style"), str):
                llm["summarization_style"] = SummarizationStyle(llm["summarization_style"])
            raw["llm"] = llm

            settings = Settings(**raw)
            logger.info("Settings loaded from %s", self.SETTINGS_FILE)
            return settings
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            logger.warning("Failed to load settings: %s, using defaults", e)
            return Settings()

    def save(self, settings: Settings) -> None:
        """Save settings to JSON file."""
        try:
            self.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            # model_dump() already converts enums to their string values
            data = settings.model_dump()
            # Don't persist empty API keys
            if not data.get("llm", {}).get("api_key"):
                data.setdefault("llm", {})["api_key"] = ""
            if not data.get("whisper", {}).get("hf_token"):
                data.setdefault("whisper", {})["hf_token"] = ""
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Settings saved to %s", self.SETTINGS_FILE)
        except OSError as e:
            logger.error("Failed to save settings: %s", e)
            raise

    def get_mic_device_info(self, pa_instance: Any) -> list[tuple[int, str]]:
        """Get list of available microphone devices.

        Returns list of (device_index, device_name) tuples.
        """
        devices = []
        for i in range(pa_instance.get_device_count()):
            dev_info = pa_instance.get_device_info_by_index(i)
            # Only include input devices with channels
            if dev_info.get("maxInputChannels", 0) > 0:
                name = dev_info.get("name", f"Device {i}")
                devices.append((i, name))
        return devices

    def get_selected_mic_name(self, pa_instance: Any) -> str:
        """Get the name of the currently selected microphone."""
        devices = self.get_mic_device_info(pa_instance)
        for idx, name in devices:
            if idx == self.recording.mic_device_id:
                return name
        return "Default"

    @property
    def recording(self) -> RecordingSettings:
        """Shortcut to access recording settings from loaded instance."""
        # This is a convenience property - in practice, load() returns a Settings object
        return RecordingSettings()
