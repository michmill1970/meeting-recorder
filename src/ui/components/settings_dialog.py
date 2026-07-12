"""Settings dialog with tabs for Recording, Whisper, and LLM configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.schemas import (
    AudioFormat,
    LLMProvider,
    SummarizationStyle,
    WhisperSpeakerMode,
)
from src.settings.manager import Settings
from src.ui.components.advanced_llm_dialog import AdvancedLLMSettingsDialog

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Modal dialog for editing application settings.

    Modern design with clear tab navigation,
    proper spacing, and accessible form layout.
    """

    def __init__(self, settings: Settings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings = settings
        self._original_settings = settings.model_copy(deep=True)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(550)
        self.setMinimumHeight(600)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the settings dialog with modern design."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #2A2A3A; border-radius: 10px; background-color: #1A1A26; }")

        # Recording tab
        self._tabs.addTab(self._create_recording_tab(), "Recording")

        # Whisper tab
        self._tabs.addTab(self._create_whisper_tab(), "Whisper")

        # LLM tab
        self._tabs.addTab(self._create_llm_tab(), "LLM")

        layout.addWidget(self._tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply,
        )
        button_box.setStyleSheet("""
            QDialogButtonBox {
                spacing: 8px;
            }
            QPushButton {
                min-width: 80px;
            }
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        layout.addWidget(button_box)

        # Load current values
        self._load_values()

    def _create_recording_tab(self) -> QWidget:
        """Create the recording settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 12, 12)

        # Save directory section
        save_dir_layout = QVBoxLayout()
        save_dir_layout.setSpacing(6)

        save_dir_label = QLabel("Save Directory:")
        save_dir_label.setStyleSheet("color: #E0E0E5; font-size: 13px; font-weight: 500;")
        save_dir_layout.addWidget(save_dir_label)

        self._save_dir_edit = QLineEdit()
        self._save_dir_edit.setText(self._settings.recording.save_dir)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(32)
        browse_btn.clicked.connect(self._browse_save_dir)

        save_dir_row = QHBoxLayout()
        save_dir_row.addWidget(self._save_dir_edit)
        save_dir_row.addWidget(browse_btn)
        save_dir_layout.addLayout(save_dir_row)
        layout.addLayout(save_dir_layout)

        # Separator
        separator1 = QLabel()
        separator1.setStyleSheet("background-color: #2A2A3A; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator1)

        # Audio format section
        format_layout = QVBoxLayout()
        format_layout.setSpacing(6)

        format_label = QLabel("Recording Format:")
        format_label.setStyleSheet("color: #E0E0E5; font-size: 13px; font-weight: 500;")
        format_layout.addWidget(format_label)

        self._format_combo = QComboBox()
        for fmt in AudioFormat:
            self._format_combo.addItem(fmt.label, fmt)
            self._format_combo.setItemData(
                self._format_combo.count() - 1, fmt.hint, Qt.ToolTipRole
            )
        idx = self._format_combo.findData(self._settings.recording.audio_format)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)
        format_layout.addWidget(self._format_combo)

        # Format hint label (updated dynamically)
        current_fmt = self._settings.recording.audio_format
        self._format_hint = QLabel(current_fmt.hint)
        self._format_hint.setWordWrap(True)
        self._format_hint.setStyleSheet("color: #6E6E7A; font-size: 11px; padding: 2px 0;")
        format_layout.addWidget(self._format_hint)

        layout.addLayout(format_layout)

        # Separator
        separator2 = QLabel()
        separator2.setStyleSheet("background-color: #2A2A3A; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator2)

        # Fixed settings section
        fixed_layout = QVBoxLayout()
        fixed_layout.setSpacing(8)

        fixed_items = [
            ("Sample Rate:", "16000 Hz (fixed for Whisper)"),
            ("Channels:", "1 (mono, fixed)"),
            ("Bit Depth:", "16-bit (fixed)"),
        ]
        for label_text, value_text in fixed_items:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)

            label = QLabel(f"{label_text}")
            label.setStyleSheet("color: #E0E0E5; font-size: 13px; font-weight: 500;")
            row_layout.addWidget(label)

            value = QLabel(value_text)
            value.setStyleSheet("color: #A0A0B0; font-size: 13px;")
            row_layout.addWidget(value)
            row_layout.addStretch()

            fixed_layout.addLayout(row_layout)

        layout.addLayout(fixed_layout)

        layout.addStretch()

        return widget

    def _create_whisper_tab(self) -> QWidget:
        """Create the Whisper settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(12)
        layout.setLabelAlignment(Qt.AlignLeft)

        # HF Token
        self._hf_token_edit = QLineEdit()
        self._hf_token_edit.setText(self._settings.whisper.hf_token)
        self._hf_token_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Hugging Face Token:", self._hf_token_edit)

        # Speaker mode
        self._speaker_mode_combo = QComboBox()
        for mode in WhisperSpeakerMode:
            self._speaker_mode_combo.addItem(mode.value, mode)
        idx = self._speaker_mode_combo.findData(self._settings.whisper.speaker_mode)
        if idx >= 0:
            self._speaker_mode_combo.setCurrentIndex(idx)
        self._speaker_mode_combo.currentIndexChanged.connect(
            self._on_speaker_mode_changed
        )
        layout.addRow("Speaker Mode:", self._speaker_mode_combo)

        # Num speakers (if specific)
        self._num_speakers_edit = QLineEdit()
        self._num_speakers_edit.setText(
            str(self._settings.whisper.num_speakers)
            if self._settings.whisper.num_speakers
            else ""
        )
        self._num_speakers_edit.setPlaceholderText("e.g., 2")
        layout.addRow("Num Speakers:", self._num_speakers_edit)

        # Min/max speakers (if range)
        self._min_speakers_edit = QLineEdit()
        self._min_speakers_edit.setText(
            str(self._settings.whisper.min_speakers)
            if self._settings.whisper.min_speakers
            else ""
        )
        self._min_speakers_edit.setPlaceholderText("e.g., 2")
        layout.addRow("Min Speakers:", self._min_speakers_edit)

        self._max_speakers_edit = QLineEdit()
        self._max_speakers_edit.setText(
            str(self._settings.whisper.max_speakers)
            if self._settings.whisper.max_speakers
            else ""
        )
        self._max_speakers_edit.setPlaceholderText("e.g., 4")
        layout.addRow("Max Speakers:", self._max_speakers_edit)

        # Ignore flips
        self._ignore_flips_edit = QLineEdit()
        self._ignore_flips_edit.setText(str(self._settings.whisper.ignore_flips))
        layout.addRow("Ignore Flips (words):", self._ignore_flips_edit)

        return widget

    def _create_llm_tab(self) -> QWidget:
        """Create the LLM settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        def _add_row(label_text: str, field_widget: QWidget) -> None:
            """Add a labeled row to the form."""
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #E0E0E5; font-size: 13px; font-weight: 500;")
            lbl.setFixedWidth(120)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lbl)
            row.addWidget(field_widget, 1)
            layout.addLayout(row)

        # Provider
        self._provider_combo = QComboBox()
        for provider in LLMProvider:
            self._provider_combo.addItem(provider.value, provider)
        idx = self._provider_combo.findData(self._settings.llm.provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        _add_row("Provider:", self._provider_combo)

        # API Key
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setText(self._settings.llm.api_key)
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        _add_row("API Key:", self._api_key_edit)

        # Base URL
        self._base_url_edit = QLineEdit()
        self._base_url_edit.setText(self._settings.llm.base_url)
        _add_row("Base URL:", self._base_url_edit)

        # Model
        self._model_edit = QLineEdit()
        self._model_edit.setText(self._settings.llm.model)
        _add_row("Model:", self._model_edit)

        # Summarization style
        self._summarization_style_combo = QComboBox()
        for style in SummarizationStyle:
            self._summarization_style_combo.addItem(style.label, style)
        idx = self._summarization_style_combo.findData(self._settings.llm.summarization_style)
        if idx >= 0:
            self._summarization_style_combo.setCurrentIndex(idx)
        self._summarization_style_combo.currentIndexChanged.connect(self._on_summarization_style_changed)
        _add_row("Summarization Style:", self._summarization_style_combo)

        # Use chat API
        self._use_chat_api_check = QCheckBox("Use Chat Completions API")
        self._use_chat_api_check.setChecked(self._settings.llm.use_chat_api)
        layout.addWidget(self._use_chat_api_check)

        # Custom prompt (only shown when style is Custom)
        self._custom_prompt_scroll = QScrollArea()
        self._custom_prompt_scroll.setFrameShape(QScrollArea.NoFrame)
        self._custom_prompt_scroll.setWidgetResizable(True)
        self._custom_prompt_scroll.setMaximumHeight(180)
        self._custom_prompt_edit = QTextEdit()
        self._custom_prompt_edit.setPlainText(self._settings.llm.custom_prompt)
        self._custom_prompt_edit.setPlaceholderText(
            "Enter your custom prompt. Use {transcript} as placeholder for the transcript text."
        )
        self._custom_prompt_scroll.setWidget(self._custom_prompt_edit)
        self._custom_prompt_scroll.setVisible(
            self._settings.llm.summarization_style == SummarizationStyle.CUSTOM
        )
        layout.addWidget(self._custom_prompt_scroll)

        # Separator
        sep = QLabel()
        sep.setStyleSheet("background-color: #2A2A3A; min-height: 1px; max-height: 1px;")
        layout.addWidget(sep)

        # Advanced LLM settings button
        self._adv_btn = QPushButton("Advanced LLM Settings…")
        self._adv_btn.setStyleSheet("""
            QPushButton {
                background-color: #2A2A3A;
                color: #E0E0E5;
                border: 1px solid #3A3A4A;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3A3A4A;
                border-color: #6C63FF;
            }
        """)
        self._adv_btn.clicked.connect(self._open_advanced_llm_settings)
        self._adv_btn.setMinimumHeight(40)
        layout.addWidget(self._adv_btn)

        return widget

    # Event handlers
    def _browse_save_dir(self) -> None:
        """Open file dialog to select save directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", self._settings.recording.save_dir
        )
        if dir_path:
            self._save_dir_edit.setText(dir_path)

    def _on_speaker_mode_changed(self, index: int) -> None:
        """Handle speaker mode change."""
        pass  # Could show/hide relevant fields

    def _on_format_changed(self, index: int) -> None:
        """Handle recording format change and update hint."""
        try:
            fmt = self._format_combo.itemData(index)
            logger.debug("Format changed index=%d, itemData=%r type=%s", index, fmt, type(fmt).__name__)
            if fmt is None:
                logger.warning("itemData returned None for index=%d", index)
                return
            if not isinstance(fmt, AudioFormat):
                # Try to convert from string value
                try:
                    fmt = AudioFormat(fmt)
                    logger.info("Converted string '%s' to AudioFormat.%s", fmt, fmt.label)
                except ValueError:
                    logger.error("Cannot convert %r to AudioFormat", fmt)
                    return
            self._format_hint.setText(fmt.hint)
            logger.debug("Hint updated to: %s", fmt.hint)
        except Exception as e:
            logger.exception("Error in _on_format_changed: %s", e)

    def _on_summarization_style_changed(self, index: int) -> None:
        """Show/hide custom prompt area when style changes."""
        style = self._summarization_style_combo.currentData()
        if style == SummarizationStyle.CUSTOM:
            self._custom_prompt_scroll.setVisible(True)
        else:
            self._custom_prompt_scroll.setVisible(False)

    def _open_advanced_llm_settings(self) -> None:
        """Open the advanced LLM generation settings dialog."""
        dialog = AdvancedLLMSettingsDialog(
            self._settings.llm.generation, parent=self
        )
        if dialog.exec() == QDialog.Accepted:
            self._settings.llm.generation = dialog.get_settings()
            logger.info("Advanced LLM settings updated: %s", self._settings.llm.generation)

    # Load/Save
    def _load_values(self) -> None:
        """Load current settings into UI (already done in constructor)."""
        pass

    def _save_values(self) -> None:
        """Save UI values to settings object."""
        self._settings.recording.save_dir = self._save_dir_edit.text()
        fmt_data = self._format_combo.currentData()
        self._settings.recording.audio_format = (
            fmt_data if isinstance(fmt_data, AudioFormat) else AudioFormat(fmt_data)
        )
        self._settings.whisper.hf_token = self._hf_token_edit.text()
        speaker_data = self._speaker_mode_combo.currentData()
        self._settings.whisper.speaker_mode = (
            speaker_data if isinstance(speaker_data, WhisperSpeakerMode) else WhisperSpeakerMode(speaker_data)
        )
        self._settings.whisper.num_speakers = (
            int(self._num_speakers_edit.text()) if self._num_speakers_edit.text() else None
        )
        self._settings.whisper.min_speakers = (
            int(self._min_speakers_edit.text()) if self._min_speakers_edit.text() else None
        )
        self._settings.whisper.max_speakers = (
            int(self._max_speakers_edit.text()) if self._max_speakers_edit.text() else None
        )
        try:
            self._settings.whisper.ignore_flips = int(self._ignore_flips_edit.text())
        except ValueError:
            self._settings.whisper.ignore_flips = 2

        provider_data = self._provider_combo.currentData()
        self._settings.llm.provider = (
            provider_data if isinstance(provider_data, LLMProvider) else LLMProvider(provider_data)
        )
        self._settings.llm.api_key = self._api_key_edit.text()
        self._settings.llm.base_url = self._base_url_edit.text()
        self._settings.llm.model = self._model_edit.text()
        self._settings.llm.use_chat_api = self._use_chat_api_check.isChecked()

        style_data = self._summarization_style_combo.currentData()
        self._settings.llm.summarization_style = (
            style_data
            if isinstance(style_data, SummarizationStyle)
            else SummarizationStyle(style_data)
        )
        self._settings.llm.custom_prompt = (
            self._custom_prompt_edit.toPlainText().strip()
        )

    def accept(self) -> None:
        """Accept and save settings."""
        self._save_values()
        super().accept()

    def apply(self) -> None:
        """Apply settings without closing dialog."""
        self._save_values()
        logger.info("Settings applied")
