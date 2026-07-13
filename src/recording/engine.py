"""Audio recording engine using PyAudio.

Handles opening audio streams, recording to WAV files,
and managing pause/resume functionality.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pyaudio

from src.models.schemas import AudioFormat, MeetingStatus, RecordingSession
from src.settings.manager import Settings

logger = logging.getLogger(__name__)


class RecordingEngine:
    """Core audio recording engine.

    Manages PyAudio streams, writes audio to WAV files in real-time,
    and supports pause/resume functionality.
    """

    # Buffer size for reading audio chunks (samples)
    CHUNK = 1024

    def __init__(self, settings: Settings):
        self._settings = settings
        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._session: Optional[RecordingSession] = None
        self._wave_file: Optional[wave.Wave_write] = None
        self._lock = threading.Lock()
        self._recording_thread: Optional[threading.Thread] = None
        self._running = False
        self._paused = False
        self._pause_start_mono: Optional[float] = None
        self._using_wav_writer: bool = True
        # Callback for audio level updates (RMS, peak)
        self._level_callback: Optional[Callable[[float, float], None]] = None
        # Store audio data in memory for callback processing
        self._audio_buffer: Optional[np.ndarray] = None
        self._audio_raw_buffer: list[bytes] = []
        self._buffer_lock = threading.Lock()

    def initialize(self) -> None:
        """Initialize PyAudio instance."""
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
            logger.info("PyAudio initialized")

    def shutdown(self) -> None:
        """Clean up PyAudio and close any open streams/files."""
        self.stop()
        if self._stream:
            self._stream.close()
            self._stream = None
        if self._pa:
            self._pa.terminate()
            self._pa = None
        logger.info("Recording engine shut down")

    @property
    def is_recording(self) -> bool:
        """Check if engine is actively recording."""
        with self._lock:
            return self._running and not self._paused

    @property
    def is_paused(self) -> bool:
        """Check if recording is paused."""
        with self._lock:
            return self._paused

    @property
    def audio_buffer(self) -> Optional[np.ndarray]:
        """Get the current audio buffer for level analysis."""
        with self._buffer_lock:
            if self._audio_buffer is not None:
                return self._audio_buffer.copy()
            return None

    def set_level_callback(self, callback: Callable[[float, float], None]) -> None:
        """Set callback for real-time audio level updates.

        Args:
            callback: Function receiving (rms_db, peak_db) values
        """
        self._level_callback = callback

    def start(self, session: RecordingSession) -> None:
        """Start recording to a new session.

        Args:
            session: The recording session to start
        """
        if self.is_recording:
            logger.warning("Already recording, stopping first")
            self.stop()

        self._session = session
        self._running = True
        self._paused = False
        session.status = MeetingStatus.RECORDING
        session.start_time = session.start_time or datetime.now()
        session.total_pause_duration = 0.0
        session.elapsed_time = 0.0

        # Create meeting directory
        session.create_meeting_dir()

        # Initialize PyAudio if needed
        self.initialize()

        # Open audio stream
        self._open_stream(session)

        # Start recording thread
        self._recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._recording_thread.start()

        logger.info("Recording started for session: %s", session.name)

    def _open_stream(self, session: RecordingSession) -> None:
        """Open PyAudio stream for recording."""
        cfg = self._settings.recording

        # Get device info
        device_index = cfg.mic_device_id
        try:
            device_info = self._pa.get_device_info_by_index(device_index)
            # Use device's native sample rate if possible, fallback to 16000
            sample_rate = int(device_info.get("defaultSampleRate", cfg.sample_rate))
            logger.info("Using device: %s (rate: %.0f Hz)",
                       device_info.get("name", "Unknown"), sample_rate)
        except Exception as e:
            logger.warning("Failed to get device info, using defaults: %s", e)
            sample_rate = cfg.sample_rate

        self._stream = self._pa.open(
            format=pyaudio.paInt16,  # 16-bit audio
            channels=cfg.channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.CHUNK,
            stream_callback=self._audio_callback,
        )
        self._stream.start_stream()

        # Initialize audio file based on format
        self._open_audio_file(session, sample_rate)

        logger.info(
            "Audio stream opened: rate=%d, channels=%d, device=%d, format=%s",
            sample_rate, cfg.channels, device_index, cfg.audio_format.value,
        )

    def _open_audio_file(self, session: RecordingSession, sample_rate: int) -> None:
        """Open audio file for recording based on configured format.

        Args:
            session: The recording session
            sample_rate: The sample rate to use
        """
        cfg = self._settings.recording
        format_type = cfg.audio_format

        if format_type == AudioFormat.WAV:
            # Use native WAV writing for WAV format (most efficient)
            filename = "recording.wav"
            self._wave_file = wave.open(str(session.meeting_dir / filename), "wb")
            self._wave_file.setnchannels(cfg.channels)
            self._wave_file.setsampwidth(cfg.sample_width)
            self._wave_file.setframerate(sample_rate)
            self._using_wav_writer = True
        else:
            # For other formats, use raw PCM buffer and convert on stop
            filename = f"recording.{format_type.value}"
            self._audio_raw_buffer: list[bytes] = []
            self._wave_file = None
            self._using_wav_writer = False

        logger.info("Recording to: %s", filename)

    def _audio_callback(self, in_data, frame_count, time_info, status_flags):
        """PyAudio stream callback - called for each audio chunk.

        Args:
            in_data: Raw audio bytes
            frame_count: Number of frames
            time_info: Timing information
            status_flags: Status flags

        Returns:
            Tuple of (None, pyaudio.paContinue) to continue recording
        """
        if not self._running or self._paused:
            return None, pyaudio.paContinue

        # Convert to numpy array for level analysis
        audio_data = np.frombuffer(in_data, dtype=np.int16)

        with self._buffer_lock:
            self._audio_buffer = audio_data

        # Write to file based on format
        if self._using_wav_writer and self._wave_file:
            self._wave_file.writeframes(in_data)
        elif not self._using_wav_writer:
            # Buffer raw PCM data for non-WAV formats
            with self._buffer_lock:
                self._audio_raw_buffer.append(in_data)

        return None, pyaudio.paContinue

    def _record_loop(self) -> None:
        """Main recording loop - tracks elapsed time."""
        last_time = time.monotonic()

        while self._running:
            if not self._paused:
                now = time.monotonic()
                delta = now - last_time
                if self._session:
                    self._session.elapsed_time += delta
                last_time = now
            time.sleep(0.1)  # Update every 100ms

    def pause(self) -> None:
        """Pause recording without stopping."""
        with self._lock:
            if not self._running or self._paused:
                return
            self._paused = True
            self._pause_start_mono = time.monotonic()

        if self._session:
            self._session.status = MeetingStatus.PAUSED
        logger.info("Recording paused")

    def resume(self) -> None:
        """Resume recording after pause."""
        with self._lock:
            if not self._running or not self._paused:
                return

            # Calculate pause duration using monotonic clock
            pause_duration = 0.0
            if self._pause_start_mono is not None:
                pause_duration = time.monotonic() - self._pause_start_mono
                self._pause_start_mono = None

        if self._session:
            self._session.total_pause_duration += pause_duration
            self._session.status = MeetingStatus.RECORDING
            self._session.pause_start_time = None

        self._paused = False
        logger.info("Recording resumed")

    def stop(self) -> None:
        """Stop recording and close all resources."""
        with self._lock:
            # Calculate remaining pause time if paused when stopped
            if self._paused and self._pause_start_mono is not None:
                pause_duration = time.monotonic() - self._pause_start_mono
                if self._session:
                    self._session.total_pause_duration += pause_duration
            self._running = False
            self._paused = False
            self._pause_start_mono = None

        # Close WAV file if using WAV writer
        if self._wave_file:
            self._wave_file.close()
            self._wave_file = None

        # Convert raw PCM to selected format if not WAV
        if not self._using_wav_writer and hasattr(self, "_audio_raw_buffer"):
            self._convert_to_format()

        # Stop stream
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning("Error closing stream: %s", e)
            self._stream = None

        # Wait for recording thread
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=2.0)

        if self._session:
            self._session.status = MeetingStatus.IDLE
            self._session.audio_path = (
                self._get_audio_path()
                if self._session.meeting_dir
                else None
            )
            logger.info(
                "Recording stopped. Elapsed: %.1fs, Paused: %.1fs",
                self._session.elapsed_time,
                self._session.total_pause_duration,
            )

        self._session = None
        with self._buffer_lock:
            self._audio_buffer = None

    def _get_audio_path(self) -> Path:
        """Get the audio file path based on current format."""
        cfg = self._settings.recording
        return self._session.meeting_dir / f"recording.{cfg.audio_format.value}"

    def _convert_to_format(self) -> None:
        """Convert raw PCM buffer to the selected audio format using ffmpeg."""
        import subprocess

        cfg = self._settings.recording
        session = self._session

        if not session or not session.meeting_dir:
            return

        # Write raw PCM to temp file
        fd, temp_pcm = tempfile.mkstemp(suffix=".pcm")
        os.close(fd)

        try:
            # Write raw PCM data (protected by buffer lock to avoid callback writes)
            with self._buffer_lock:
                chunks = list(self._audio_raw_buffer)

            with open(temp_pcm, "wb") as f:
                for chunk in chunks:
                    f.write(chunk)

            # Convert to target format using ffmpeg
            output_path = self._get_audio_path()
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "s16le",  # 16-bit signed little-endian
                "-ar", str(cfg.sample_rate),
                "-ac", str(cfg.channels),
                "-i", temp_pcm,
            ]

            # Add format-specific options
            if cfg.audio_format == AudioFormat.FLAC:
                ffmpeg_cmd.extend([
                    "-c:a", "flac",
                    "-compression_level", "6",
                ])
            elif cfg.audio_format == AudioFormat.OPUS:
                ffmpeg_cmd.extend([
                    "-c:a", "libopus",
                    "-b:a", "128k",
                ])
            elif cfg.audio_format == AudioFormat.MP3:
                ffmpeg_cmd.extend([
                    "-c:a", "libmp3lame",
                    "-b:a", "192k",
                ])
            elif cfg.audio_format == AudioFormat.OGG:
                ffmpeg_cmd.extend([
                    "-c:a", "libvorbis",
                    "-b:a", "128k",
                ])

            ffmpeg_cmd.append(str(output_path))

            subprocess.run(ffmpeg_cmd, check=True)
            logger.info("Converted PCM to %s: %s", cfg.audio_format.value, output_path)

        except subprocess.CalledProcessError as e:
            logger.error("Failed to convert audio: %s", e)
        except OSError as e:
            logger.error("Failed to write audio: %s", e)
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_pcm)
            except OSError:
                pass

        # Clear buffer (protected by lock to avoid callback writes)
        with self._buffer_lock:
            self._audio_raw_buffer = []
