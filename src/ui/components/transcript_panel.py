"""Transcript display panel."""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class TranscriptPanel(QWidget):
    """Panel for displaying the meeting transcript.

    Modern design with improved readability,
    proper spacing, and accessible text display.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the transcript panel with modern design."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlaceholderText("Transcript will appear here after recording...")
        layout.addWidget(self._text_edit)

    def set_transcript(self, text: str) -> None:
        """Set the transcript text."""
        self._text_edit.setPlainText(text)
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()

    def append_transcript(self, text: str) -> None:
        """Append text to the transcript."""
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()

    def clear(self) -> None:
        """Clear the transcript."""
        self._text_edit.clear()
