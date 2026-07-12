"""Recording panel with controls for start/pause/stop, mic selection, and gain control."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.audio_meter import AudioMeter

logger = logging.getLogger(__name__)


class RecordingPanel(QWidget):
    """Panel with recording controls.

    Modern design with clear visual hierarchy, spacious layout,
    and intuitive control grouping.
    """

    # Signals
    record_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    mic_selected = Signal(int)
    gain_changed = Signal(float)
    auto_mode_toggled = Signal(bool)
    meeting_selected = Signal(str)  # meeting_dir path
    reprocess_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the recording panel UI with two tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setObjectName("recordingTabs")

        # === Tab 1: New Recording ===
        new_recording_tab = self._create_new_recording_tab()
        self._tabs.addTab(new_recording_tab, "New Recording")

        # === Tab 2: Existing Recordings ===
        existing_tab = self._create_existing_recordings_tab()
        self._tabs.addTab(existing_tab, "Existing Recordings")

        layout.addWidget(self._tabs)

    def _create_new_recording_tab(self) -> QWidget:
        """Create the New Recording tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title with modern typography
        title = QLabel("Recording")
        title.setObjectName("title")
        layout.addWidget(title)

        # Recording buttons - Primary actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._record_btn = QPushButton("Record")
        self._record_btn.setObjectName("recordButton")
        self._record_btn.setFixedHeight(40)
        self._record_btn.clicked.connect(self._on_record_clicked)
        btn_layout.addWidget(self._record_btn)

        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setObjectName("pauseButton")
        self._pause_btn.setFixedHeight(40)
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        btn_layout.addWidget(self._pause_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self._stop_btn)

        layout.addLayout(btn_layout)

        # Microphone selection - Elevated card
        mic_group = QGroupBox("Microphone")
        mic_layout = QVBoxLayout(mic_group)
        mic_layout.setContentsMargins(12, 14, 12, 12)
        mic_layout.setSpacing(8)

        self._mic_combo = QComboBox()
        self._mic_combo.setMinimumWidth(180)
        self._mic_combo.currentIndexChanged.connect(self._on_mic_selected)
        mic_layout.addWidget(self._mic_combo)

        layout.addWidget(mic_group)

        # Audio meter - Elevated card
        meter_frame = QFrame()
        meter_frame.setObjectName("raised")
        meter_layout = QVBoxLayout(meter_frame)
        meter_layout.setContentsMargins(8, 8, 8, 8)
        meter_layout.setSpacing(6)

        self._meter_label = QLabel("Audio Level")
        self._meter_label.setStyleSheet("font-size: 12px; color: #6E6E7A; font-weight: 500;")
        meter_layout.addWidget(self._meter_label)

        self._meter = AudioMeter()
        meter_layout.addWidget(self._meter)

        layout.addWidget(meter_frame)

        # Gain control - Elevated card
        gain_group = QGroupBox("Gain Control")
        gain_layout = QVBoxLayout(gain_group)
        gain_layout.setContentsMargins(12, 14, 12, 12)
        gain_layout.setSpacing(10)

        # Auto mode toggle
        auto_layout = QHBoxLayout()
        self._auto_checkbox = QCheckBox("Auto Mode")
        self._auto_checkbox.setChecked(True)
        self._auto_checkbox.stateChanged.connect(self._on_auto_mode_toggled)
        auto_layout.addWidget(self._auto_checkbox)
        auto_layout.addStretch()
        gain_layout.addLayout(auto_layout)

        # Manual gain slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Gain:"))
        self._gain_slider = QSlider(Qt.Horizontal)
        self._gain_slider.setRange(-120, 120)  # -12 to +12 dB (scaled by 10)
        self._gain_slider.setValue(0)
        self._gain_slider.valueChanged.connect(self._on_gain_changed)
        self._gain_slider.setEnabled(False)  # Disabled in auto mode
        slider_layout.addWidget(self._gain_slider)
        self._gain_label = QLabel("0.0 dB")
        self._gain_label.setFixedWidth(60)
        self._gain_label.setStyleSheet("color: #A0A0B0; font-size: 12px;")
        slider_layout.addWidget(self._gain_label)
        gain_layout.addLayout(slider_layout)

        layout.addWidget(gain_group)

        layout.addStretch()

        return tab

    def _create_existing_recordings_tab(self) -> QWidget:
        """Create the Existing Recordings tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title
        title = QLabel("Existing Recordings")
        title.setObjectName("title")
        layout.addWidget(title)

        # Instruction label
        instr = QLabel("Select a saved meeting to view its transcript and reprocess it.")
        instr.setStyleSheet("color: #6E6E7A; font-size: 11px;")
        instr.setWordWrap(True)
        layout.addWidget(instr)

        # Meeting list (stretches to fill available space)
        self._meeting_list = QListWidget()
        self._meeting_list.setSelectionMode(QListWidget.SingleSelection)
        self._meeting_list.itemClicked.connect(self._on_meeting_selected)
        layout.addWidget(self._meeting_list, 1)

        # Reprocess button (anchored to bottom)
        self._reprocess_btn = QPushButton("Reprocess Selected")
        self._reprocess_btn.setObjectName("secondaryButton")
        self._reprocess_btn.setFixedHeight(36)
        self._reprocess_btn.setEnabled(False)
        self._reprocess_btn.clicked.connect(self._on_reprocess_clicked)
        layout.addWidget(self._reprocess_btn)

        return tab

    # Signal handlers
    def _on_record_clicked(self) -> None:
        self.record_clicked.emit()

    def _on_pause_clicked(self) -> None:
        self.pause_clicked.emit()

    def _on_stop_clicked(self) -> None:
        self.stop_clicked.emit()

    def _on_mic_selected(self, index: int) -> None:
        self.mic_selected.emit(index)

    def _on_gain_changed(self, value: int) -> None:
        gain = value / 10.0
        self._gain_label.setText(f"{gain:.1f} dB")
        self.gain_changed.emit(gain)

    def _on_auto_mode_toggled(self, state: int) -> None:
        is_auto = state == Qt.Checked
        self._gain_slider.setEnabled(not is_auto)
        self.auto_mode_toggled.emit(is_auto)

    def _on_meeting_selected(self, item: QListWidgetItem) -> None:
        meeting_dir = item.data(Qt.UserRole)
        self.meeting_selected.emit(meeting_dir)

    def _on_reprocess_clicked(self) -> None:
        self.reprocess_clicked.emit()

    # Public API
    def set_microphones(self, devices: list[tuple[int, str]]) -> None:
        """Populate microphone dropdown."""
        self._mic_combo.clear()
        for idx, name in devices:
            self._mic_combo.addItem(name, idx)

    def select_microphone(self, device_id: int) -> None:
        """Select a microphone by ID."""
        for i in range(self._mic_combo.count()):
            if self._mic_combo.itemData(i) == device_id:
                self._mic_combo.setCurrentIndex(i)
                break

    def update_meter(self, rms_db: float, peak_db: float, gain_db: float) -> None:
        """Update the audio meter display."""
        self._meter.update_levels(rms_db, peak_db, gain_db)

    def set_meter_calibration(self, is_calibrating: bool, is_auto_mode: bool) -> None:
        """Update meter calibration indicator."""
        self._meter.set_calibration_state(is_calibrating, is_auto_mode)

    def set_recording_state(self, is_recording: bool, is_paused: bool) -> None:
        """Update button states based on recording state."""
        self._record_btn.setEnabled(not is_recording)
        self._pause_btn.setEnabled(is_recording and not is_paused)
        self._stop_btn.setEnabled(is_recording)

        if is_recording:
            if is_paused:
                self._pause_btn.setText("Resume")
            else:
                self._pause_btn.setText("Pause")

    def set_gain_enabled(self, enabled: bool) -> None:
        """Enable or disable manual gain control."""
        self._gain_slider.setEnabled(enabled)

    def populate_meetings(self, meetings: list[tuple[str, str]]) -> None:
        """Populate the meeting list.

        Args:
            meetings: List of (display_name, meeting_dir_path) tuples
        """
        self._meeting_list.clear()
        for display_name, meeting_dir in meetings:
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, meeting_dir)
            self._meeting_list.addItem(item)

    def set_reprocess_enabled(self, enabled: bool) -> None:
        """Enable or disable the reprocess button."""
        self._reprocess_btn.setEnabled(enabled)

    def get_selected_meeting_dir(self) -> Optional[str]:
        """Get the currently selected meeting directory path."""
        items = self._meeting_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return None

    def switch_to_tab(self, tab_index: int) -> None:
        """Switch to the specified tab."""
        self._tabs.setCurrentIndex(tab_index)
