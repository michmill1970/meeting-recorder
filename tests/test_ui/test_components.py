"""Unit tests for UI components."""

import pytest
from unittest.mock import MagicMock, patch

# Check if Qt is available
import sys
from tests.conftest import _qt_available

if not _qt_available:
    # Skip all UI tests if Qt is not available
    pytest.skip("Qt not available, skipping UI tests", allow_module_level=True)

from src.ui.components.audio_meter import AudioMeter
from src.ui.components.recording_panel import RecordingPanel
from src.ui.components.transcript_panel import TranscriptPanel
from src.ui.components.summary_panel import SummaryPanel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout


class TestAudioMeter:
    """Tests for AudioMeter widget."""

    def test_initialization(self, qtbot) -> None:
        meter = AudioMeter()
        assert meter._rms_db == -60.0
        assert meter._peak_db == -60.0
        assert meter._gain_db == 0.0
        assert meter._display_rms == -60.0
        assert meter._display_peak == -60.0

    def test_update_levels(self) -> None:
        meter = AudioMeter()
        meter.update_levels(-20.0, -15.0, 2.5)
        assert meter._rms_db == -20.0
        assert meter._peak_db == -15.0
        assert meter._gain_db == 2.5

    def test_set_calibration_state(self) -> None:
        meter = AudioMeter()
        meter.set_calibration_state(True, True)
        assert meter._is_calibrating is True
        assert meter._is_auto_mode is True

        meter.set_calibration_state(False, False)
        assert meter._is_calibrating is False
        assert meter._is_auto_mode is False

    def test_get_color_for_level_green(self) -> None:
        meter = AudioMeter()
        color = meter._get_color_for_level(-20.0)
        # Should be green (green channel is dominant)
        assert color.green() > color.red()

    def test_get_color_for_level_yellow(self) -> None:
        meter = AudioMeter()
        color = meter._get_color_for_level(-5.0)
        # Should be yellow (high R and G)
        assert color.red() > 150 and color.green() > 150

    def test_get_color_for_level_red(self) -> None:
        meter = AudioMeter()
        color = meter._get_color_for_level(0.0)
        # Should be red (red channel is dominant)
        assert color.red() > color.green()

    def test_get_level_text(self) -> None:
        meter = AudioMeter()
        meter.update_levels(-20.0, -15.0, 2.5)
        text = meter.get_level_text()
        assert "RMS: -20.0 dB" in text
        assert "Peak: -15.0 dB" in text
        assert "Gain: +2.5 dB" in text


class TestRecordingPanel:
    """Tests for RecordingPanel widget."""

    def test_initialization(self) -> None:
        panel = RecordingPanel()
        assert panel._record_btn is not None
        assert panel._pause_btn is not None
        assert panel._stop_btn is not None
        assert panel._mic_combo is not None
        assert panel._meter is not None
        assert panel._gain_slider is not None

    def test_has_two_tabs(self) -> None:
        panel = RecordingPanel()
        assert panel._tabs is not None
        assert panel._tabs.count() == 2

    def test_tab_names(self) -> None:
        panel = RecordingPanel()
        assert panel._tabs.tabText(0) == "New Recording"
        assert panel._tabs.tabText(1) == "Existing Recordings"

    def test_default_tab_is_new_recording(self) -> None:
        panel = RecordingPanel()
        assert panel._tabs.currentIndex() == 0

    def test_reprocess_button_exists(self) -> None:
        panel = RecordingPanel()
        # Access the reprocess button from the second tab
        existing_tab = panel._tabs.widget(1)
        from PySide6.QtWidgets import QVBoxLayout
        layout = existing_tab.layout()
        assert layout is not None
        # Find the reprocess button (it's the last widget before the stretch)
        reprocess_btn = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "text") and widget.text() == "Reprocess Selected":
                    reprocess_btn = widget
                    break
        assert reprocess_btn is not None
        assert reprocess_btn.isEnabled() is False

    def test_button_states_initial(self) -> None:
        panel = RecordingPanel()
        # Record should be enabled, Pause and Stop disabled
        assert panel._record_btn.isEnabled() is True
        assert panel._pause_btn.isEnabled() is False
        assert panel._stop_btn.isEnabled() is False

    def test_set_recording_state_recording(self) -> None:
        panel = RecordingPanel()
        panel.set_recording_state(True, False)
        assert panel._record_btn.isEnabled() is False
        assert panel._pause_btn.isEnabled() is True
        assert panel._stop_btn.isEnabled() is True

    def test_set_recording_state_paused(self) -> None:
        panel = RecordingPanel()
        panel.set_recording_state(True, True)
        assert panel._pause_btn.text() == "Resume"

    def test_set_recording_state_idle(self) -> None:
        panel = RecordingPanel()
        panel.set_recording_state(False, False)
        assert panel._record_btn.isEnabled() is True
        assert panel._pause_btn.isEnabled() is False
        assert panel._stop_btn.isEnabled() is False

    def test_set_microphones(self) -> None:
        panel = RecordingPanel()
        devices = [(0, "Mic 1"), (1, "Mic 2"), (2, "Mic 3")]
        panel.set_microphones(devices)
        assert panel._mic_combo.count() == 3
        assert panel._mic_combo.itemText(0) == "Mic 1"
        assert panel._mic_combo.itemText(1) == "Mic 2"

    def test_select_microphone(self) -> None:
        panel = RecordingPanel()
        panel.set_microphones([(0, "Mic 1"), (1, "Mic 2")])
        panel.select_microphone(1)
        assert panel._mic_combo.currentIndex() == 1

    def test_update_meter(self) -> None:
        panel = RecordingPanel()
        panel.update_meter(-20.0, -15.0, 2.5)
        # Verify the meter was updated (we can't easily test QPainter)
        assert panel._meter._rms_db == -20.0

    def test_set_meter_calibration(self) -> None:
        panel = RecordingPanel()
        panel.set_meter_calibration(True, True)
        assert panel._meter._is_calibrating is True

    def test_set_gain_enabled(self) -> None:
        panel = RecordingPanel()
        panel.set_gain_enabled(False)
        assert panel._gain_slider.isEnabled() is False
        panel.set_gain_enabled(True)
        assert panel._gain_slider.isEnabled() is True

    def test_populate_meetings(self) -> None:
        panel = RecordingPanel()
        meetings = [
            ("Meeting A (100 KB, .wav)", "/path/meeting-a"),
            ("Meeting B (200 KB, .wav)", "/path/meeting-b"),
        ]
        panel.populate_meetings(meetings)
        assert panel._meeting_list.count() == 2
        assert panel._meeting_list.item(0).text() == "Meeting A (100 KB, .wav)"
        assert panel._meeting_list.item(0).data(Qt.UserRole) == "/path/meeting-a"
        assert panel._meeting_list.item(1).data(Qt.UserRole) == "/path/meeting-b"

    def test_populate_meetings_empty(self) -> None:
        panel = RecordingPanel()
        panel.populate_meetings([])
        assert panel._meeting_list.count() == 0

    def test_get_selected_meeting_dir(self) -> None:
        panel = RecordingPanel()
        panel.populate_meetings([
            ("Meeting A", "/path/meeting-a"),
            ("Meeting B", "/path/meeting-b"),
        ])
        # No selection
        assert panel.get_selected_meeting_dir() is None
        # Select first item
        panel._meeting_list.setCurrentRow(0)
        assert panel.get_selected_meeting_dir() == "/path/meeting-a"
        # Select second item
        panel._meeting_list.setCurrentRow(1)
        assert panel.get_selected_meeting_dir() == "/path/meeting-b"

    def test_set_reprocess_enabled(self) -> None:
        panel = RecordingPanel()
        existing_tab = panel._tabs.widget(1)
        layout = existing_tab.layout()
        assert layout is not None
        # Find the reprocess button
        reprocess_btn = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "text") and widget.text() == "Reprocess Selected":
                    reprocess_btn = widget
                    break
        assert reprocess_btn is not None
        panel.set_reprocess_enabled(True)
        assert reprocess_btn.isEnabled() is True
        panel.set_reprocess_enabled(False)
        assert reprocess_btn.isEnabled() is False

    def test_switch_to_tab(self) -> None:
        panel = RecordingPanel()
        assert panel._tabs.currentIndex() == 0
        panel.switch_to_tab(1)
        assert panel._tabs.currentIndex() == 1
        panel.switch_to_tab(0)
        assert panel._tabs.currentIndex() == 0

    def test_meeting_selected_signal(self, qtbot) -> None:
        panel = RecordingPanel()
        panel.populate_meetings([
            ("Meeting A", "/path/meeting-a"),
        ])
        # Connect to a handler
        received = []
        def on_selected(path):
            received.append(path)
        panel.meeting_selected.connect(on_selected)
        # Simulate click
        qtbot.addWidget(panel)
        panel._meeting_list.setCurrentRow(0)
        # The signal is emitted on itemClicked, not setCurrentRow
        # So we emit it manually for this test
        panel._meeting_list.itemClicked.emit(panel._meeting_list.item(0))
        assert len(received) == 1
        assert received[0] == "/path/meeting-a"

    def test_reprocess_clicked_signal(self, qtbot) -> None:
        panel = RecordingPanel()
        received = []
        def on_reprocess():
            received.append(True)
        panel.reprocess_clicked.connect(on_reprocess)
        qtbot.addWidget(panel)
        # Emit the signal directly (button is in a hidden tab, mouseClick unreliable)
        panel.reprocess_clicked.emit()
        assert len(received) == 1


class TestTranscriptPanel:
    """Tests for TranscriptPanel widget."""

    def test_initialization(self) -> None:
        panel = TranscriptPanel()
        assert panel._text_edit is not None
        assert panel._text_edit.isReadOnly() is True

    def test_set_transcript(self) -> None:
        panel = TranscriptPanel()
        text = "[00:01] Speaker 1: Hello"
        panel.set_transcript(text)
        assert panel._text_edit.toPlainText() == text

    def test_append_transcript(self) -> None:
        panel = TranscriptPanel()
        panel.append_transcript("Line 1\n")
        panel.append_transcript("Line 2\n")
        assert "Line 1" in panel._text_edit.toPlainText()
        assert "Line 2" in panel._text_edit.toPlainText()

    def test_clear(self) -> None:
        panel = TranscriptPanel()
        panel.set_transcript("Some text")
        panel.clear()
        assert panel._text_edit.toPlainText() == ""


class TestSummaryPanel:
    """Tests for SummaryPanel widget."""

    def test_initialization(self) -> None:
        panel = SummaryPanel()
        assert panel._text_browser is not None

    def test_set_summary(self) -> None:
        panel = SummaryPanel()
        text = "Test summary content"
        panel.set_summary(text)
        assert panel._text_browser.document().toPlainText() == text

    def test_clear(self) -> None:
        panel = SummaryPanel()
        panel.set_summary("Some summary")
        panel.clear()
        assert panel._text_browser.document().toPlainText() == ""
