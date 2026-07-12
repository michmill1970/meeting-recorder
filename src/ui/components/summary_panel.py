"""Summary display panel."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class SummaryPanel(QWidget):
    """Panel for displaying the LLM-generated meeting summary.

    Modern design with markdown rendering,
    proper spacing, and accessible text display.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the summary panel with markdown rendering."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text_browser = QTextBrowser()
        self._text_browser.setOpenExternalLinks(True)
        self._text_browser.setPlaceholderText(
            "Summary will appear here after processing..."
        )
        layout.addWidget(self._text_browser)

    def set_summary(self, text: str) -> None:
        """Set the summary text (rendered as markdown)."""
        self._text_browser.setMarkdown(text)

    def clear(self) -> None:
        """Clear the summary."""
        self._text_browser.clear()
