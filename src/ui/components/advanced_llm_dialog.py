"""Advanced LLM generation settings dialog.

Provides fine-grained control over LLM sampling, repetition, and diversity
parameters. Organized in grouped sections with preset profiles for quick
selection.

Design inspired by Jan.ai Model Settings panel:
- Preset selector at the top (Focused / Balanced / Creative)
- Grouped parameter sections (Sampling, Repetition, Diversity)
- Slider + editable number input for continuous parameters
- Plain-language tooltips for non-technical users
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.settings.manager import LLMGenerationSettings

logger = logging.getLogger(__name__)


class _SliderInputRow(QWidget):
    """A row with a slider and an editable number input side by side."""

    def __init__(
        self,
        label: str,
        tooltip: str,
        value: float,
        min_val: float,
        max_val: float,
        decimals: int = 2,
        step: float = 0.05,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._decimals = decimals
        self._step = step

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Label
        self._label = QLabel(label)
        self._label.setToolTip(tooltip)
        self._label.setStyleSheet("color: #A0A0B0; font-size: 13px;")
        layout.addWidget(self._label)

        layout.addStretch()

        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(int((max_val - min_val) / step * 100))
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(int((max_val - min_val) / (step * 10) * 100))
        self._slider.setValue(int((value - min_val) / step))
        self._slider.setFixedWidth(200)
        self._slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #2A2A3A; height: 6px; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #6C63FF; width: 16px; margin: -5px 0; border-radius: 8px; } "
            "QSlider::handle:horizontal:hover { background: #7B73FF; } "
            "QSlider::sub-page:horizontal { background: #6C63FF; border-radius: 3px; }"
        )
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        # Number input
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(f"{min_val}")
        self._edit.setText(self._format_value(value))
        self._edit.setFixedWidth(72)
        self._edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._edit.setStyleSheet(
            "QLineEdit { background-color: #1A1A26; color: #E0E0E5; border: 1px solid #2A2A3A; "
            "border-radius: 6px; padding: 4px 8px; font-size: 13px; font-family: monospace; } "
            "QLineEdit:focus { border-color: #6C63FF; }"
        )
        self._edit.textChanged.connect(self._on_edit_changed)
        layout.addWidget(self._edit)

    @staticmethod
    def _format_value(value: float) -> str:
        return f"{value:.2f}"

    def _on_slider_changed(self, value: int) -> None:
        """Update the number input when the slider moves."""
        min_val = 0.0
        step = self._step
        fvalue = min_val + value * step
        fvalue = round(fvalue, self._decimals)
        self._edit.blockSignals(True)
        self._edit.setText(self._format_value(fvalue))
        self._edit.blockSignals(False)

    def _on_edit_changed(self, text: str) -> None:
        """Update the slider when the number input changes."""
        try:
            fvalue = float(text)
            min_val = 0.0
            step = self._step
            slider_val = int(round((fvalue - min_val) / step))
            slider_val = max(self._slider.minimum(), min(self._slider.maximum(), slider_val))
            self._slider.blockSignals(True)
            self._slider.setValue(slider_val)
            self._slider.blockSignals(False)
        except (ValueError, ZeroDivisionError):
            pass

    def get_value(self) -> float:
        """Return the current value."""
        try:
            return float(self._edit.text())
        except ValueError:
            return 0.0

    def set_value(self, value: float) -> None:
        """Set the value, syncing slider and input."""
        min_val = 0.0
        step = self._step
        slider_val = int(round((value - min_val) / step))
        slider_val = max(self._slider.minimum(), min(self._slider.maximum(), slider_val))
        self._slider.blockSignals(True)
        self._edit.blockSignals(True)
        self._slider.setValue(slider_val)
        self._edit.setText(self._format_value(value))
        self._slider.blockSignals(False)
        self._edit.blockSignals(False)


class _SpinBoxRow(QWidget):
    """An integer spin box widget (label is provided by _make_param_row)."""

    def __init__(
        self,
        label: str,
        tooltip: str,
        value: int,
        min_val: int,
        max_val: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addStretch()

        self._spin = QSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setValue(value)
        self._spin.setFixedWidth(80)
        self._spin.setStyleSheet(
            "QSpinBox { background-color: #1A1A26; color: #E0E0E5; border: 1px solid #2A2A3A; "
            "border-radius: 6px; padding: 4px 8px; font-size: 13px; font-family: monospace; } "
            "QSpinBox:focus { border-color: #6C63FF; } "
            "QSpinBox::up-button, QSpinBox::down-button { width: 16px; }"
        )
        self._spin.setToolTip(tooltip)
        layout.addWidget(self._spin)

    def get_value(self) -> int:
        """Return the current value."""
        return self._spin.value()

    def set_value(self, value: int) -> None:
        """Set the value."""
        self._spin.setValue(value)


class AdvancedLLMSettingsDialog(QDialog):
    """Modal dialog for advanced LLM generation parameters.

    Organized into three sections:
    - Sampling (temperature, top_p, top_k)
    - Repetition (repetition_penalty)
    - Diversity (presence_penalty, frequency_penalty)

    Preset profiles (Focused, Balanced, Creative) provide quick defaults.
    """

    PRESET_LABELS = {
        "focused": "Focused",
        "balanced": "Balanced",
        "creative": "Creative",
    }

    PARAM_DESCRIPTIONS = {
        "temperature": (
            "How creative vs. predictable the output is.\n"
            "Low (0.1) = consistent, factual. High (0.7) = creative, varied."
        ),
        "top_p": (
            "Controls word variety by filtering unlikely words.\n"
            "Works with temperature. Lower = more focused choices."
        ),
        "top_k": (
            "How many word choices the model considers at each step.\n"
            "Smaller = more focused. Larger = more variety."
        ),
        "repetition_penalty": (
            "How strongly the model avoids repeating phrases.\n"
            "1.0 = no penalty. Higher values reduce repetition."
        ),
        "presence_penalty": (
            "Encourages the model to talk about new topics.\n"
            "Positive values make the model more likely to introduce new subjects."
        ),
        "frequency_penalty": (
            "Reduces repeated use of the same words/phrases.\n"
            "Positive values make the model less likely to repeat words."
        ),
    }

    def __init__(
        self,
        generation_settings: LLMGenerationSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = generation_settings
        self.setWindowTitle("Advanced LLM Settings")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        title = QLabel("Advanced LLM Settings")
        title.setObjectName("title")
        root.addWidget(title)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet("color: #A0A0B0; font-size: 13px; font-weight: 500;")
        preset_layout.addWidget(preset_label)

        self._preset_combo = QComboBox()
        for preset in LLMGenerationSettings.presets():
            self._preset_combo.addItem(self.PRESET_LABELS[preset], preset)
        idx = self._preset_combo.findData(self._settings.preset)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self._preset_combo.setToolTip("Quick-select a configuration profile")
        preset_layout.addWidget(self._preset_combo)

        self._preset_desc = QLabel(self._settings.preset_description)
        self._preset_desc.setWordWrap(True)
        self._preset_desc.setStyleSheet("color: #6E6E7A; font-size: 11px; padding: 2px 0;")
        preset_layout.addWidget(self._preset_desc)
        preset_layout.addStretch()
        root.addLayout(preset_layout)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        scroll_layout.addLayout(self._create_sampling_section())

        sep1 = QLabel()
        sep1.setStyleSheet("background-color: #2A2A3A; min-height: 1px; max-height: 1px;")
        scroll_layout.addWidget(sep1)

        scroll_layout.addLayout(self._create_repetition_section())

        sep2 = QLabel()
        sep2.setStyleSheet("background-color: #2A2A3A; min-height: 1px; max-height: 1px;")
        scroll_layout.addWidget(sep2)

        scroll_layout.addLayout(self._create_diversity_section())
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        root.addWidget(scroll)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setStyleSheet(
            "QDialogButtonBox { spacing: 8px; } "
            "QPushButton { min-width: 80px; }"
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

    def _create_sampling_section(self) -> QVBoxLayout:
        """Create the Sampling parameters section."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(4)
        title_lbl = QLabel("Sampling")
        title_lbl.setStyleSheet("color: #E8E8ED; font-size: 13px; font-weight: 600;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        self._temp_row = _SliderInputRow(
            "Temperature",
            self.PARAM_DESCRIPTIONS["temperature"],
            self._settings.temperature,
            min_val=0.0,
            max_val=2.0,
            decimals=2,
            step=0.05,
        )
        layout.addLayout(self._make_param_row(
            "Temperature",
            self.PARAM_DESCRIPTIONS["temperature"],
            self._temp_row,
        ))

        self._top_p_row = _SliderInputRow(
            "Top P",
            self.PARAM_DESCRIPTIONS["top_p"],
            self._settings.top_p,
            min_val=0.0,
            max_val=1.0,
            decimals=2,
            step=0.01,
        )
        layout.addLayout(self._make_param_row(
            "Top P",
            self.PARAM_DESCRIPTIONS["top_p"],
            self._top_p_row,
        ))

        self._top_k_row = _SpinBoxRow(
            "Top K",
            self.PARAM_DESCRIPTIONS["top_k"],
            self._settings.top_k,
            min_val=1,
            max_val=256,
        )
        layout.addLayout(self._make_param_row(
            "Top K",
            self.PARAM_DESCRIPTIONS["top_k"],
            self._top_k_row,
        ))

        return layout

    def _create_repetition_section(self) -> QVBoxLayout:
        """Create the Repetition parameters section."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(4)
        title_lbl = QLabel("Repetition")
        title_lbl.setStyleSheet("color: #E8E8ED; font-size: 13px; font-weight: 600;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        self._rep_penalty_row = _SliderInputRow(
            "Repetition Penalty",
            self.PARAM_DESCRIPTIONS["repetition_penalty"],
            self._settings.repetition_penalty,
            min_val=1.0,
            max_val=2.0,
            decimals=2,
            step=0.01,
        )
        layout.addLayout(self._make_param_row(
            "Repetition Penalty",
            self.PARAM_DESCRIPTIONS["repetition_penalty"],
            self._rep_penalty_row,
        ))

        return layout

    def _create_diversity_section(self) -> QVBoxLayout:
        """Create the Diversity parameters section."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(4)
        title_lbl = QLabel("Diversity")
        title_lbl.setStyleSheet("color: #E8E8ED; font-size: 13px; font-weight: 600;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        self._presence_row = _SliderInputRow(
            "Presence Penalty",
            self.PARAM_DESCRIPTIONS["presence_penalty"],
            self._settings.presence_penalty,
            min_val=-2.0,
            max_val=2.0,
            decimals=2,
            step=0.05,
        )
        layout.addLayout(self._make_param_row(
            "Presence Penalty",
            self.PARAM_DESCRIPTIONS["presence_penalty"],
            self._presence_row,
        ))

        self._freq_row = _SliderInputRow(
            "Frequency Penalty",
            self.PARAM_DESCRIPTIONS["frequency_penalty"],
            self._settings.frequency_penalty,
            min_val=-2.0,
            max_val=2.0,
            decimals=2,
            step=0.05,
        )
        layout.addLayout(self._make_param_row(
            "Frequency Penalty",
            self.PARAM_DESCRIPTIONS["frequency_penalty"],
            self._freq_row,
        ))

        return layout

    @staticmethod
    def _make_param_row(label: str, tooltip: str, widget: QWidget) -> QHBoxLayout:
        """Create a single parameter row with label + widget."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        lbl = QLabel(label)
        lbl.setToolTip(tooltip)
        lbl.setStyleSheet("color: #A0A0B0; font-size: 13px;")
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(widget)
        return layout

    def _on_preset_changed(self, index: int) -> None:
        """Apply preset values when the preset changes."""
        preset = self._preset_combo.currentData()
        if not preset:
            return
        preset_settings = LLMGenerationSettings.from_preset(preset)

        self._temp_row.set_value(preset_settings.temperature)
        self._top_p_row.set_value(preset_settings.top_p)
        self._top_k_row.set_value(preset_settings.top_k)
        self._rep_penalty_row.set_value(preset_settings.repetition_penalty)
        self._presence_row.set_value(preset_settings.presence_penalty)
        self._freq_row.set_value(preset_settings.frequency_penalty)

        self._preset_desc.setText(preset_settings.preset_description)

    def get_settings(self) -> LLMGenerationSettings:
        """Return current settings from the dialog."""
        return LLMGenerationSettings(
            temperature=self._temp_row.get_value(),
            top_p=self._top_p_row.get_value(),
            top_k=self._top_k_row.get_value(),
            repetition_penalty=self._rep_penalty_row.get_value(),
            presence_penalty=self._presence_row.get_value(),
            frequency_penalty=self._freq_row.get_value(),
            preset=self._preset_combo.currentData() or "balanced",
        )
