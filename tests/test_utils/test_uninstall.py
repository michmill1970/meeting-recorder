"""Tests for uninstall script."""

import os
import stat
from pathlib import Path

import pytest


class TestUninstallScript:
    """Tests for the uninstall.sh script."""

    def test_uninstall_script_exists(self) -> None:
        """Test that uninstall.sh exists."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        assert script_path.exists(), "uninstall.sh not found"

    def test_uninstall_script_is_executable(self) -> None:
        """Test that uninstall.sh is executable."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        assert os.access(script_path, os.X_OK), "uninstall.sh is not executable"

    def test_uninstall_script_has_shebang(self) -> None:
        """Test that uninstall.sh has a proper shebang line."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        first_line = script_path.read_text().splitlines()[0]
        assert first_line.startswith("#!/usr/bin/env bash"), "Missing bash shebang"

    def test_uninstall_script_removes_venv(self) -> None:
        """Test that uninstall script references venv removal."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert ".local/share/meeting-recorder" in content, "Missing venv removal"

    def test_uninstall_script_removes_launchers(self) -> None:
        """Test that uninstall script removes launcher scripts."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert "meeting-recorder" in content, "Missing meeting-recorder launcher"
        assert "whisper-setup" in content, "Missing whisper-setup launcher"

    def test_uninstall_script_removes_config(self) -> None:
        """Test that uninstall script removes config directory."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert ".config/meeting-recorder" in content, "Missing config removal"

    def test_uninstall_script_removes_meetings(self) -> None:
        """Test that uninstall script removes meetings directory."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert "Documents/MeetingRecorder" in content, "Missing meetings removal"

    def test_uninstall_script_warns_about_meetings(self) -> None:
        """Test that uninstall script warns before deleting meetings."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert "Are you sure" in content or "continue" in content.lower(), \
            "Missing confirmation prompt for meetings deletion"

    def test_uninstall_script_handles_hf_cache(self) -> None:
        """Test that uninstall script handles Hugging Face cache."""
        script_path = Path(__file__).parent.parent.parent / "uninstall.sh"
        content = script_path.read_text()
        assert "huggingface" in content.lower(), "Missing HF cache handling"
        assert "whisper" in content.lower(), "Missing whisper model removal"
        assert "pyannote" in content.lower(), "Missing pyannote model removal"
