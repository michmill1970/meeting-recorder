"""Whisper transcription client.

Wraps the whisper-diarization transcribe.py as a subprocess call.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

from src.models.schemas import RecordingSession
from src.settings.manager import Settings

logger = logging.getLogger(__name__)

# Path to the vendored transcribe.py
WHISPER_DIR = Path(__file__).parent.parent.parent / "whisper-diarization"
WHISPER_SCRIPT = WHISPER_DIR / "transcribe.py"


class WhisperClient:
    """Client for running whisper-diarization transcription.

    Calls transcribe.py as a subprocess and captures output.
    """

    # Progress patterns from transcribe.py output
    PROGRESS_PATTERNS = [
        re.compile(r"Loading Whisper via MLX.*"),
        re.compile(r"Transcribing full audio.*"),
        re.compile(r"Transcribed (\d+) words"),
        re.compile(r"Running speaker diarization.*"),
        re.compile(r"Found (\d+) speaker intervals"),
        re.compile(r"Transcoding to 16 kHz mono WAV"),
        re.compile(r"Audio duration:.*"),
    ]

    def __init__(self, settings: Settings):
        self._settings = settings
        self._progress_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function receiving progress message strings
        """
        self._progress_callback = callback

    def transcribe(
        self,
        audio_path: Path,
        session: RecordingSession,
    ) -> Optional[str]:
        """Transcribe an audio file using whisper-diarization.

        Args:
            audio_path: Path to the WAV audio file
            session: Recording session (for HF token from settings)

        Returns:
            Transcript text, or None if transcription failed
        """
        if not WHISPER_SCRIPT.exists():
            logger.error("Whisper script not found: %s", WHISPER_SCRIPT)
            return None

        hf_token = self._settings.whisper.hf_token
        if not hf_token:
            logger.error("Hugging Face token not configured")
            return None

        # Build command
        cmd = [
            "python3", str(WHISPER_SCRIPT),
            str(audio_path),
            "--hf-token", hf_token,
        ]

        # Add speaker constraints if configured
        whisper_cfg = self._settings.whisper
        if whisper_cfg.speaker_mode.value == "specific" and whisper_cfg.num_speakers:
            cmd.extend(["--speakers", str(whisper_cfg.num_speakers)])
        elif whisper_cfg.speaker_mode.value == "range":
            if whisper_cfg.min_speakers:
                cmd.extend(["--min-speakers", str(whisper_cfg.min_speakers)])
            if whisper_cfg.max_speakers:
                cmd.extend(["--max-speakers", str(whisper_cfg.max_speakers)])

        if whisper_cfg.ignore_flips > 0:
            cmd.extend(["--ignore-flips", str(whisper_cfg.ignore_flips)])

        # Save transcript to file
        transcript_path = session.meeting_dir / "transcript.txt"
        cmd.extend(["-o", str(transcript_path)])

        logger.info("Running whisper transcription: %s", " ".join(cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            output_lines = []
            assert process.stdout is not None

            for line in process.stdout:
                output_lines.append(line.rstrip())
                self._emit_progress(line.rstrip())

                # Check if transcription is complete (transcribe.py exits after output)
                if "Saved to" in line or process.poll() is not None:
                    break

            process.wait()

            if process.returncode != 0:
                logger.error(
                    "Whisper transcription failed with return code %d",
                    process.returncode,
                )
                logger.error("Output: %s", "\n".join(output_lines[-10:]))
                return None

            # Read transcript from file
            if transcript_path.exists():
                transcript = transcript_path.read_text(encoding="utf-8")
                session.transcript_path = transcript_path
                logger.info("Transcription complete: %d characters", len(transcript))
                return transcript
            else:
                logger.error("Transcript file not created")
                return None

        except FileNotFoundError:
            logger.error(
                "python3 not found. Install Python 3.12+ with whisper-diarization deps."
            )
            return None
        except OSError as e:
            logger.error("Failed to run whisper transcription: %s", e)
            return None

    def _emit_progress(self, message: str) -> None:
        """Emit progress message via callback."""
        if self._progress_callback:
            self._progress_callback(message)
        else:
            logger.debug("[Whisper] %s", message)
