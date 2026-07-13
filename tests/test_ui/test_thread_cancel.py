"""Unit tests for thread cancellation support.

Tests TranscribeThread and SummarizeThread cancel behaviour.
These threads live in src.ui.main_window and inherit from QThread,
so they cannot be instantiated in headless environments without Qt.
In such environments, cancel logic is covered by the client/provider tests
(test_whisper_client.py, test_llm.py).
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QEventLoop, QObject, Qt

try:
    from PySide6.QtTest import QTest
except ImportError:
    QTest = None


def _wait_for_thread(thread: QObject, timeout_ms: int = 10000) -> None:
    """Block the test event loop until *thread* emits ``finished``.

    Uses a local ``QEventLoop`` so that Qt signals are processed while
    waiting.  This is the correct way to wait on a ``QThread`` in a test
    (``QTest.qWait`` only sleeps and does not process events).

    Ensures a ``QApplication`` exists (needed for ``QEventLoop``).
    """
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication(sys.argv)

    loop = QEventLoop()
    thread.finished.connect(loop.quit, Qt.QueuedConnection)
    thread.start()
    loop.exec()  # processes events until thread.finished


def _has_qt():
    """Check if Qt widgets are available (not mocked)."""
    mod = sys.modules.get("PySide6.QtCore")
    if mod is None:
        return False
    # If it's a MagicMock, Qt was mocked (headless environment)
    return not isinstance(mod, MagicMock)


def _has_real_qthread():
    """Check if QThread is a real class (not mocked)."""
    try:
        from PySide6.QtCore import QThread
        return not isinstance(QThread, type) or hasattr(QThread, "__module__")
    except Exception:
        return False


# ---------------------------------------------------------------------------
# TranscribeThread cancel tests (require real Qt)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_qt(), reason="Qt not available (headless environment)")
class TestTranscribeThreadCancel:
    """Tests for TranscribeThread cancellation."""

    def _make_thread(self, cancelled_ref=None):
        """Helper to create a TranscribeThread with mocked dependencies."""
        from src.ui.main_window import TranscribeThread
        mock_client = MagicMock()
        import tempfile
        session_dir = Path(tempfile.mkdtemp())
        audio_path = session_dir / "recording.wav"
        audio_path.touch()
        thread = TranscribeThread(
            session_dir=session_dir,
            audio_path=audio_path,
            whisper_client=mock_client,
            cancelled_ref=cancelled_ref,
        )
        return thread, mock_client, session_dir

    def test_is_cancelled_with_no_ref(self) -> None:
        """_is_cancelled() should return False when no cancelled_ref is set."""
        thread, _, _ = self._make_thread(cancelled_ref=None)
        assert thread._is_cancelled() is False

    def test_is_cancelled_with_ref_true(self) -> None:
        """_is_cancelled() should return True when ref returns True."""
        thread, _, _ = self._make_thread(cancelled_ref=lambda: True)
        assert thread._is_cancelled() is True

    def test_is_cancelled_with_ref_false(self) -> None:
        """_is_cancelled() should return False when ref returns False."""
        thread, _, _ = self._make_thread(cancelled_ref=lambda: False)
        assert thread._is_cancelled() is False

    def test_cancel_before_start_emits_error(self) -> None:
        """Thread should emit error and finish immediately if already cancelled."""
        cancelled = [True]
        thread, mock_client, _ = self._make_thread(
            cancelled_ref=lambda: cancelled[0]
        )

        errors = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)

        _wait_for_thread(thread)

        assert len(errors) == 1
        assert "cancelled" in errors[0].lower()
        assert mock_client.cancel.call_count == 1

    def test_cancel_flag_false_succeeds(self) -> None:
        """Thread should succeed normally when not cancelled."""
        cancelled = [False]
        thread, mock_client, _ = self._make_thread(
            cancelled_ref=lambda: cancelled[0]
        )

        errors = []
        transcripts = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        def on_transcript(text):
            transcripts.append(text)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)
        thread.transcript_ready.connect(on_transcript, Qt.DirectConnection)
        mock_client.transcribe.return_value = "Test transcript"

        _wait_for_thread(thread)

        assert len(transcripts) == 1
        assert transcripts[0] == "Test transcript"
        assert len(errors) == 0
        assert mock_client.cancel.call_count == 0

    def test_cancel_after_transcription_emits_error(self) -> None:
        """If cancelled after transcription succeeds, should emit error."""
        cancelled = [True]
        call_count = [0]

        def transcribe_side_effect(*args, **kwargs):
            call_count[0] += 1
            return "Test transcript"

        thread, mock_client, _ = self._make_thread(
            cancelled_ref=lambda: cancelled[0] if call_count[0] <= 1 else True
        )

        errors = []
        transcripts = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        def on_transcript(text):
            transcripts.append(text)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)
        thread.transcript_ready.connect(on_transcript, Qt.DirectConnection)
        mock_client.transcribe.side_effect = transcribe_side_effect

        _wait_for_thread(thread)

        assert len(errors) == 1
        assert "cancelled" in errors[0].lower()
        assert len(transcripts) == 0


# ---------------------------------------------------------------------------
# SummarizeThread cancel tests (require real Qt)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_qt(), reason="Qt not available (headless environment)")
class TestSummarizeThreadCancel:
    """Tests for SummarizeThread cancellation."""

    def _make_thread(self, cancelled_ref=None):
        """Helper to create a SummarizeThread with mocked dependencies."""
        from src.ui.main_window import SummarizeThread
        mock_client = MagicMock()
        thread = SummarizeThread(
            transcript="Test transcript",
            llm_client=mock_client,
            cancelled_ref=cancelled_ref,
        )
        return thread, mock_client, None

    def test_is_cancelled_with_no_ref(self) -> None:
        """_is_cancelled() should return False when no cancelled_ref is set."""
        thread, _, _ = self._make_thread(cancelled_ref=None)
        assert thread._is_cancelled() is False

    def test_is_cancelled_with_ref_true(self) -> None:
        """_is_cancelled() should return True when ref returns True."""
        thread, _, _ = self._make_thread(cancelled_ref=lambda: True)
        assert thread._is_cancelled() is True

    def test_is_cancelled_with_ref_false(self) -> None:
        """_is_cancelled() should return False when ref returns False."""
        thread, _, _ = self._make_thread(cancelled_ref=lambda: False)
        assert thread._is_cancelled() is False

    def test_cancel_before_start_emits_error(self) -> None:
        """Thread should emit error and finish immediately if already cancelled."""
        cancelled = [True]
        thread, mock_client, _ = self._make_thread(
            cancelled_ref=lambda: cancelled[0]
        )

        errors = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)

        _wait_for_thread(thread)

        assert len(errors) == 1
        assert "cancelled" in errors[0].lower()
        assert mock_client.cancel.call_count == 1

    def test_cancel_flag_false_succeeds(self) -> None:
        """Thread should succeed normally when not cancelled."""
        cancelled = [False]
        thread, mock_client, _ = self._make_thread(
            cancelled_ref=lambda: cancelled[0]
        )

        errors = []
        summaries = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        def on_summary(text):
            summaries.append(text)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)
        thread.summary_ready.connect(on_summary, Qt.DirectConnection)

        async def mock_summarize(transcript):
            return "Test summary"

        mock_client.summarize = mock_summarize

        _wait_for_thread(thread)

        assert len(summaries) == 1
        assert summaries[0] == "Test summary"
        assert len(errors) == 0
        assert mock_client.cancel.call_count == 0

    def test_cancelled_error_from_provider(self) -> None:
        """Thread should handle CancelledError from async summarize."""
        cancelled = [True]
        call_count = [0]

        async def mock_summarize(transcript):
            call_count[0] += 1
            if call_count[0] == 1:
                raise asyncio.CancelledError("Summarization cancelled by user")
            return "Should not reach"

        mock_client = MagicMock()
        mock_client.summarize = mock_summarize
        mock_client.cancel = lambda: cancelled.__setitem__(0, True)

        from src.ui.main_window import SummarizeThread

        thread = SummarizeThread(
            transcript="Test transcript",
            llm_client=mock_client,
            cancelled_ref=lambda: cancelled[0] if call_count[0] <= 1 else True,
        )

        errors = []

        def on_error(msg):
            errors.append(msg)
            thread.finished.emit()

        thread.error.connect(on_error, Qt.DirectConnection)

        _wait_for_thread(thread)

        assert len(errors) == 1
        assert "cancelled" in errors[0].lower()
