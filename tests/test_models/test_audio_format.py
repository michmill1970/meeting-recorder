"""Tests for AudioFormat enum."""

import pytest

from src.models.schemas import AudioFormat


class TestAudioFormat:
    """Tests for the AudioFormat enum."""

    def test_audio_format_values(self) -> None:
        """Test that all format values are correct."""
        assert AudioFormat.WAV.value == "wav"
        assert AudioFormat.FLAC.value == "flac"
        assert AudioFormat.OPUS.value == "opus"
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.OGG.value == "ogg"

    def test_audio_format_labels(self) -> None:
        """Test human-readable labels for each format."""
        assert AudioFormat.WAV.label == "WAV (Uncompressed)"
        assert AudioFormat.FLAC.label == "FLAC (Lossless)"
        assert AudioFormat.OPUS.label == "OPUS (Recommended)"
        assert AudioFormat.MP3.label == "MP3 (Universal)"
        assert AudioFormat.OGG.label == "OGG Vorbis"

    def test_audio_format_hints(self) -> None:
        """Test that hints describe format characteristics."""
        assert "WAV" in AudioFormat.WAV.hint.lower() or "largest" in AudioFormat.WAV.hint.lower()
        assert "lossless" in AudioFormat.FLAC.hint.lower()
        assert "recommended" in AudioFormat.OPUS.hint.lower() or "best" in AudioFormat.OPUS.hint.lower()
        assert "universal" in AudioFormat.MP3.hint.lower() or "compatibility" in AudioFormat.MP3.hint.lower()
        assert "vorbis" in AudioFormat.OGG.hint.lower() or "open-source" in AudioFormat.OGG.hint.lower()

    def test_audio_format_extensions(self) -> None:
        """Test file extensions match format values."""
        assert AudioFormat.WAV.extension == "wav"
        assert AudioFormat.FLAC.extension == "flac"
        assert AudioFormat.OPUS.extension == "opus"
        assert AudioFormat.MP3.extension == "mp3"
        assert AudioFormat.OGG.extension == "ogg"

    def test_audio_format_iteration(self) -> None:
        """Test that all formats can be iterated."""
        formats = list(AudioFormat)
        assert len(formats) == 5
        assert AudioFormat.WAV in formats
        assert AudioFormat.FLAC in formats
        assert AudioFormat.OPUS in formats
        assert AudioFormat.MP3 in formats
        assert AudioFormat.OGG in formats
