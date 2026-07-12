"""Speaker rename dialog for labeling speakers after transcription."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# Pattern to match speaker labels in transcript: "[MM:SS] Speaker N: text"
# Also handles variations like "[MM:SS]Speaker N:" or "[M:SS] Speaker N:"
SPEAKER_PATTERN = re.compile(r"\[?\d{1,2}:\d{2}\]?\s+Speaker\s+(\d+):\s*")


class SpeakerRenameDialog(QDialog):
    """Dialog for renaming speakers after transcription.

    Shows a list of detected speakers with input fields to rename them.
    Provides a preview of the transcript with renamed speakers.
    """

    speakers_confirmed = Signal(list)  # List of (old_name, new_name) tuples
    use_defaults = Signal()
    cancelled = Signal()

    # Color palette for speakers
    _SPEAKER_COLORS = [
        "#6C63FF",  # Purple
        "#FF6B6B",  # Red
        "#4ECDC4",  # Teal
        "#FFE66D",  # Yellow
        "#A8E6CF",  # Mint
        "#FF8B94",  # Pink
        "#95E1D3",  # Seafoam
        "#F38181",  # Coral
    ]

    def __init__(
        self,
        transcript_text: str,
        meeting_dir: Path,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._transcript_text = transcript_text
        self._meeting_dir = meeting_dir
        self._speaker_names: dict[str, str] = {}  # old_name -> new_name
        self._detected_speakers: list[str] = []  # List of "Speaker N" strings
        self._ui_initialized = False

        # Detect speakers BEFORE building UI so we know how many inputs to create
        self._detect_speakers()
        self._setup_ui()
        self._ui_initialized = True

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Rename Speakers")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Rename Speakers")
        title.setObjectName("title")
        layout.addWidget(title)

        # Instruction
        instr = QLabel(
            "Give each speaker a meaningful name. "
            "This will update the transcript before summarization."
        )
        instr.setStyleSheet("color: #6E6E7A; font-size: 12px;")
        instr.setWordWrap(True)
        layout.addWidget(instr)

        # Speaker renaming form
        speaker_group = QGroupBox("Detected Speakers")
        speaker_group.setObjectName("raised")
        speaker_layout = QFormLayout(speaker_group)
        speaker_layout.setSpacing(8)
        speaker_layout.setLabelAlignment(Qt.AlignLeft)

        self._speaker_inputs: dict[str, QLineEdit] = {}
        self._selected_speaker: Optional[str] = None

        for i, speaker in enumerate(self._detected_speakers):
            color = self._SPEAKER_COLORS[i % len(self._SPEAKER_COLORS)]
            row_layout = QHBoxLayout()

            # Color indicator
            indicator = QLabel()
            indicator.setFixedWidth(12)
            indicator.setFixedHeight(12)
            indicator.setStyleSheet(
                f"background-color: {color}; border-radius: 6px;"
            )
            row_layout.addWidget(indicator)

            # Speaker label
            label = QLabel(speaker)
            label.setStyleSheet("color: #E0E0E5; font-size: 13px; min-width: 100px;")
            row_layout.addWidget(label)

            # Rename input
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Name for {speaker}")
            input_field.setFixedHeight(32)
            input_field.setStyleSheet(
                "QLineEdit { "
                "background-color: #1A1A26; "
                "border: 1px solid #2A2A3A; "
                "border-radius: 6px; "
                "padding: 4px 8px; "
                "color: #E0E0E5; "
                "font-size: 12px; "
                "}"
                "QLineEdit:focus { border: 1px solid #6C63FF; }"
            )
            self._speaker_inputs[speaker] = input_field
            # Install event filter to detect focus gain
            input_field.installEventFilter(self)
            input_field.textChanged.connect(self._update_preview)
            row_layout.addWidget(input_field)

            speaker_layout.addRow(row_layout)

        layout.addWidget(speaker_group)

        # Preview section
        preview_label = QLabel("Preview (first 5 lines):")
        preview_label.setStyleSheet("color: #A0A0B0; font-size: 12px; font-weight: 500;")
        layout.addWidget(preview_label)

        self._preview_edit = QTextEdit()
        self._preview_edit.setReadOnly(True)
        self._preview_edit.setMaximumHeight(150)
        self._preview_edit.setStyleSheet(
            "QTextEdit { "
            "background-color: #1A1A26; "
            "border: 1px solid #2A2A3A; "
            "border-radius: 6px; "
            "padding: 8px; "
            "color: #E0E0E5; "
            "font-family: monospace; "
            "font-size: 11px; "
            "}"
        )
        self._update_preview()
        layout.addWidget(self._preview_edit)

        # Update preview on input changes
        for input_field in self._speaker_inputs.values():
            input_field.textChanged.connect(self._update_preview)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self._cancel_btn)

        self._use_defaults_btn = QPushButton("Use Default Labels")
        self._use_defaults_btn.setFixedHeight(36)
        self._use_defaults_btn.clicked.connect(self._on_use_defaults)
        button_layout.addWidget(self._use_defaults_btn)

        self._confirm_btn = QPushButton("Apply & Continue")
        self._confirm_btn.setObjectName("recordButton")
        self._confirm_btn.setFixedHeight(36)
        self._confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(self._confirm_btn)

        layout.addLayout(button_layout)

    def _detect_speakers(self) -> None:
        """Detect unique speakers from the transcript text."""
        if not self._transcript_text:
            logger.warning("Transcript text is empty, no speakers to detect")
            self._detected_speakers = []
            return

        speakers = set()
        for match in SPEAKER_PATTERN.finditer(self._transcript_text):
            speaker_num = match.group(1)
            speakers.add(f"Speaker {speaker_num}")

        self._detected_speakers = sorted(speakers, key=lambda s: int(s.split()[-1]))
        logger.info("Detected %d speakers: %s", len(self._detected_speakers), self._detected_speakers)

    def _populate_speaker_inputs(self) -> None:
        """Set initial values in speaker input fields."""
        # Optionally pre-populate with common names if detected from context
        pass

    def eventFilter(self, obj: object, event: Any) -> bool:
        """Event filter to detect focus changes on speaker input fields."""
        if obj in self._speaker_inputs.values():
            speaker = None
            for s, inp in self._speaker_inputs.items():
                if inp == obj:
                    speaker = s
                    break
            if speaker:
                self._select_speaker(speaker)
        return super().eventFilter(obj, event)

    def _select_speaker(self, speaker: str) -> None:
        """Mark a speaker as selected and update the preview."""
        if not self._ui_initialized:
            return
        self._selected_speaker = speaker
        self._update_preview()

    def _get_speaker_lines(self, speaker: str) -> list[str]:
        """Get the first 5 lines matching the selected speaker.

        Searches for both the original label (e.g., 'Speaker 1') and
        the new name the user has typed in the input field.
        """
        input_field = self._speaker_inputs.get(speaker)
        if not input_field:
            return []

        new_name = input_field.text().strip()
        lines = self._transcript_text.split("\n")
        matching = []

        for line in lines:
            if not line.strip():
                continue
            matched = False

            # Check for original speaker label: "[MM:SS] Speaker N: text"
            speaker_match = SPEAKER_PATTERN.match(line)
            if speaker_match:
                speaker_num = speaker_match.group(1)
                original_label = f"Speaker {speaker_num}"
                if original_label == speaker:
                    matched = True

            # If a new name has been entered, also match against it
            if not matched and new_name:
                # Pattern: "[MM:SS] NewName: text" or "NewName: text"
                new_pattern = re.compile(
                    r"\[?\d{1,2}:\d{2}\]?\s+" + re.escape(new_name) + r":\s*"
                )
                if new_pattern.match(line):
                    matched = True

            if matched:
                matching.append(line)
                if len(matching) >= 5:
                    break

        return matching

    def _update_preview(self) -> None:
        """Update the preview text.

        If a speaker is selected, shows the first 5 utterances for that speaker.
        Otherwise shows the first 5 lines of the full transcript with all renames applied.
        """
        if self._selected_speaker:
            # Show first 5 lines for the selected speaker
            lines = self._get_speaker_lines(self._selected_speaker)
            self._preview_edit.setText("\n".join(lines))
        else:
            # Fallback: show first 5 lines with all renames applied
            preview_text = self._transcript_text
            for old_name, input_field in self._speaker_inputs.items():
                new_name = input_field.text().strip()
                if new_name:
                    # Pattern specific to this speaker to avoid cross-replacement
                    pattern = re.compile(
                        r"(\[?\d{1,2}:\d{2}\]?\s+)" + re.escape(old_name) + r":\s*"
                    )
                    replacement = r"\1" + new_name + ": "
                    preview_text = pattern.sub(replacement, preview_text)
            lines = preview_text.split("\n")[:5]
            self._preview_edit.setText("\n".join(lines))

    def _on_confirm(self) -> None:
        """Apply speaker renames and save updated transcript."""
        renames = []
        for old_name, input_field in self._speaker_inputs.items():
            new_name = input_field.text().strip()
            if new_name:
                renames.append((old_name, new_name))

        if not renames:
            QMessageBox.information(
                self,
                "No Changes",
                "No speaker names were entered. Click 'Use Default Labels' to proceed with default names.",
            )
            return

        # Apply renames to transcript
        updated_text = self._transcript_text
        for old_name, new_name in renames:
            # old_name is like "Speaker 1" — build a pattern specific to this speaker
            # so we don't accidentally replace other speakers
            pattern = re.compile(
                r"(\[?\d{1,2}:\d{2}\]?\s+)" + re.escape(old_name) + r":\s*"
            )
            replacement = r"\1" + new_name + ": "
            updated_text = pattern.sub(replacement, updated_text)

        # Save updated transcript
        transcript_path = self._meeting_dir / "transcript.txt"
        try:
            transcript_path.write_text(updated_text, encoding="utf-8")
            logger.info("Updated transcript with speaker renames: %s", renames)
        except Exception as e:
            logger.error("Failed to save updated transcript: %s", e)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save updated transcript:\n{e}",
            )
            return

        self._speaker_names = dict(renames)
        self.speakers_confirmed.emit(renames)
        self.accept()

    def _on_use_defaults(self) -> None:
        """Proceed with default speaker labels."""
        self.use_defaults.emit()
        self.accept()

    def _on_cancel(self) -> None:
        """Cancel the renaming process."""
        self.cancelled.emit()
        self.reject()
