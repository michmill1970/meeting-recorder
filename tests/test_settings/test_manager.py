"""Unit tests for settings manager."""

import json
import os
from pathlib import Path

import pytest

from src.models.schemas import LLMProvider, WhisperSpeakerMode
from src.settings.manager import Settings, SettingsManager


class TestSettingsModel:
    """Tests for the Settings pydantic model."""

    def test_default_settings(self) -> None:
        settings = Settings()
        assert settings.recording.mic_device_id == 0
        assert settings.recording.sample_rate == 16000
        assert settings.recording.channels == 1
        assert settings.recording.sample_width == 2
        assert settings.audio_leveling.auto_mode is True
        assert settings.audio_leveling.noise_floor_offset_db == 10.0
        assert settings.audio_leveling.dead_air_timeout_sec == 60.0
        assert settings.audio_leveling.max_gain_db == 12.0
        assert settings.audio_leveling.gain_ramp_rate_db_per_sec == 0.5
        assert settings.whisper.hf_token == ""
        assert settings.whisper.speaker_mode == WhisperSpeakerMode.AUTO
        assert settings.whisper.ignore_flips == 2
        assert settings.llm.provider == LLMProvider.OPENAI
        assert settings.llm.api_key == ""
        assert settings.llm.model == "gpt-4o"

    def test_settings_model_dump(self) -> None:
        settings = Settings()
        settings.whisper.hf_token = "test_token"
        settings.llm.api_key = "test_key"
        data = settings.model_dump()
        assert data["whisper"]["hf_token"] == "test_token"
        assert data["llm"]["api_key"] == "test_key"

    def test_settings_model_dump_filtered_empty_keys(self) -> None:
        settings = Settings()
        data = settings.model_dump_filtered()
        assert data["llm"]["api_key"] == ""
        assert data["whisper"]["hf_token"] == ""


class TestSettingsManager:
    """Tests for SettingsManager persistence."""

    def test_load_defaults_when_no_file(self, settings_manager: SettingsManager) -> None:
        settings = settings_manager.load()
        assert isinstance(settings, Settings)
        assert settings.whisper.hf_token == ""
        assert settings.llm.api_key == ""

    def test_save_and_load(self, settings_manager: SettingsManager) -> None:
        settings = Settings()
        settings.whisper.hf_token = "my_hf_token"
        settings.llm.api_key = "my_api_key"
        settings.llm.provider = LLMProvider.ANTHROPIC
        settings.llm.model = "claude-sonnet-4-20250514"
        settings.whisper.speaker_mode = WhisperSpeakerMode.SPECIFIC
        settings.whisper.num_speakers = 3

        settings_manager.save(settings)

        # Load back
        loaded = settings_manager.load()
        assert loaded.whisper.hf_token == "my_hf_token"
        assert loaded.llm.api_key == "my_api_key"
        assert loaded.llm.provider == LLMProvider.ANTHROPIC
        assert loaded.llm.model == "claude-sonnet-4-20250514"
        assert loaded.whisper.speaker_mode == WhisperSpeakerMode.SPECIFIC
        assert loaded.whisper.num_speakers == 3

    def test_save_creates_directory(self, settings_manager: SettingsManager) -> None:
        settings = Settings()
        settings_manager.save(settings)
        assert settings_manager.SETTINGS_DIR.exists()
        assert settings_manager.SETTINGS_FILE.exists()

    def test_load_invalid_json(self, settings_manager: SettingsManager) -> None:
        # Write invalid JSON
        settings_manager.SETTINGS_FILE.write_text("{invalid json}", encoding="utf-8")
        settings = settings_manager.load()
        # Should return defaults, not crash
        assert isinstance(settings, Settings)

    def test_get_mic_device_info(self, settings_manager: SettingsManager, mock_pyaudio: any) -> None:
        devices = settings_manager.get_mic_device_info(mock_pyaudio)
        assert len(devices) == 2
        assert devices[0] == (0, "Test Microphone")
        assert devices[1] == (1, "System Default")

    def test_get_selected_mic_name(self, settings_manager: SettingsManager, mock_pyaudio: any) -> None:
        settings = Settings()
        settings.recording.mic_device_id = 0
        name = settings_manager.get_selected_mic_name(mock_pyaudio)
        assert name == "Test Microphone"

    def test_get_selected_mic_name_not_found(self, settings_manager: SettingsManager, mock_pyaudio: any) -> None:
        settings = Settings()
        settings.recording.mic_device_id = 99  # Non-existent
        # When device not found, should return first available mic name
        name = settings_manager.get_selected_mic_name(mock_pyaudio)
        assert name == "Test Microphone"  # Returns first device when ID not found

    def test_settings_file_path_custom(self, tmp_dir: Path) -> None:
        custom_path = tmp_dir / "custom_settings.json"
        manager = SettingsManager(custom_path)
        assert manager.SETTINGS_FILE == custom_path
        assert manager.SETTINGS_DIR == tmp_dir

    def test_save_roundtrip_all_fields(self, settings_manager: SettingsManager) -> None:
        """Test that all settings fields survive a save/load cycle."""
        settings = Settings()
        settings.recording.mic_device_id = 5
        settings.recording.save_dir = "/custom/path"
        settings.audio_leveling.auto_mode = False
        settings.audio_leveling.rms_target_db = -25.0
        settings.audio_leveling.noise_floor_offset_db = 15.0
        settings.audio_leveling.dead_air_timeout_sec = 90.0
        settings.audio_leveling.max_gain_db = 18.0
        settings.audio_leveling.gain_ramp_rate_db_per_sec = 1.0
        settings.audio_leveling.calibration_duration_sec = 10.0
        settings.whisper.hf_token = "token123"
        settings.whisper.speaker_mode = WhisperSpeakerMode.RANGE
        settings.whisper.min_speakers = 2
        settings.whisper.max_speakers = 5
        settings.whisper.ignore_flips = 3
        settings.llm.provider = LLMProvider.OLLAMA
        settings.llm.api_key = ""
        settings.llm.base_url = "http://localhost:11434"
        settings.llm.model = "llama3"

        settings_manager.save(settings)
        loaded = settings_manager.load()

        assert loaded.recording.mic_device_id == 5
        assert loaded.recording.save_dir == "/custom/path"
        assert loaded.audio_leveling.auto_mode is False
        assert loaded.audio_leveling.rms_target_db == -25.0
        assert loaded.audio_leveling.noise_floor_offset_db == 15.0
        assert loaded.audio_leveling.dead_air_timeout_sec == 90.0
        assert loaded.audio_leveling.max_gain_db == 18.0
        assert loaded.audio_leveling.gain_ramp_rate_db_per_sec == 1.0
        assert loaded.audio_leveling.calibration_duration_sec == 10.0
        assert loaded.whisper.hf_token == "token123"
        assert loaded.whisper.speaker_mode == WhisperSpeakerMode.RANGE
        assert loaded.whisper.min_speakers == 2
        assert loaded.whisper.max_speakers == 5
        assert loaded.whisper.ignore_flips == 3
        assert loaded.llm.provider == LLMProvider.OLLAMA
        assert loaded.llm.base_url == "http://localhost:11434"
        assert loaded.llm.model == "llama3"
