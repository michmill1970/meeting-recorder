"""Theme system for the meeting recorder application.

Provides multiple color schemes that can be selected in Settings.
Each theme defines a palette of colors and a full QSS stylesheet
generated from the existing dark theme with token substitutions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


_THEME_PALETTES: dict[str, dict[str, str]] = {
    "modern_dark": {
        "label": "Modern Dark",
        "description": "The current purple-yellow-dark scheme.",
        "bg_primary": "#0A0A0F",
        "bg_surface": "#12121A",
        "bg_elevated": "#1A1A26",
        "bg_interactive": "#24243A",
        "bg_hover": "#2A2A42",
        "border": "#2A2A3A",
        "border_light": "#3A3A5A",
        "border_dark": "#4A4A5A",
        "text_primary": "#E8E8ED",
        "text_secondary": "#A0A0B0",
        "text_tertiary": "#6E6E7A",
        "text_disabled": "#4A4A5A",
        "text_highlight": "#E0E0E5",
        "text_white": "#FFFFFF",
        "primary": "#6C63FF",
        "primary_hover": "#7B73FF",
        "primary_pressed": "#5B52EE",
        "accent": "#FBBF24",
        "accent_hover": "#FCD34D",
        "accent_pressed": "#F59E0B",
        "accent_text": "#0A0A0F",
        "destructive": "#3A3A5A",
        "destructive_hover": "#4A4A6A",
        "status_success": "#4ADE80",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#60A5FA",
        "scrollbar": "#3A3A5A",
        "scrollbar_hover": "#4A4A6A",
        "scrollbar_bg": "#0A0A0F",
        "selection": "#24243A",
        "focus": "#6C63FF",
        "tab_selected_border": "#6C63FF",
        "tab_hover": "#1E1E2A",
        "input_bg": "#1A1A26",
        "input_focus_bg": "#1E1E2A",
        "progress_bg": "#2A2A3A",
        "menu_hover": "#24243A"
    },
    "slate_sky": {
        "label": "Slate & Sky",
        "description": "Calm, professional \u2014 like Linear and Notion.",
        "bg_primary": "#020617",
        "bg_surface": "#0F172A",
        "bg_elevated": "#1E293B",
        "bg_interactive": "#283547",
        "bg_hover": "#334155",
        "border": "#1E293B",
        "border_light": "#334155",
        "border_dark": "#475569",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_tertiary": "#64748B",
        "text_disabled": "#475569",
        "text_highlight": "#CBD5E1",
        "text_white": "#F8FAFC",
        "primary": "#38BDF8",
        "primary_hover": "#7DD3FC",
        "primary_pressed": "#0284C7",
        "accent": "#38BDF8",
        "accent_hover": "#7DD3FC",
        "accent_pressed": "#0284C7",
        "accent_text": "#020617",
        "destructive": "#334155",
        "destructive_hover": "#475569",
        "status_success": "#4ADE80",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#60A5FA",
        "scrollbar": "#334155",
        "scrollbar_hover": "#475569",
        "scrollbar_bg": "#020617",
        "selection": "#1E3A5A",
        "focus": "#38BDF8",
        "tab_selected_border": "#38BDF8",
        "tab_hover": "#1E293B",
        "input_bg": "#1E293B",
        "input_focus_bg": "#243447",
        "progress_bg": "#334155",
        "menu_hover": "#1E293B"
    },
    "indigo_cyan": {
        "label": "Indigo & Cyan",
        "description": "Sharp, intelligent, tech-forward \u2014 signals AI-powered.",
        "bg_primary": "#020617",
        "bg_surface": "#0B1220",
        "bg_elevated": "#1E293B",
        "bg_interactive": "#253049",
        "bg_hover": "#2D3B55",
        "border": "#1E293B",
        "border_light": "#2D3B55",
        "border_dark": "#3D4F6B",
        "text_primary": "#EEF2FF",
        "text_secondary": "#C7D2FE",
        "text_tertiary": "#818CF8",
        "text_disabled": "#4338CA",
        "text_highlight": "#E0E7FF",
        "text_white": "#FAFAFC",
        "primary": "#4F46E5",
        "primary_hover": "#6366F1",
        "primary_pressed": "#4338CA",
        "accent": "#22D3EE",
        "accent_hover": "#67E8F9",
        "accent_pressed": "#06B6D4",
        "accent_text": "#020617",
        "destructive": "#2D3B55",
        "destructive_hover": "#3D4F6B",
        "status_success": "#4ADE80",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#60A5FA",
        "scrollbar": "#2D3B55",
        "scrollbar_hover": "#3D4F6B",
        "scrollbar_bg": "#020617",
        "selection": "#1E1B4B",
        "focus": "#6366F1",
        "tab_selected_border": "#6366F1",
        "tab_hover": "#1E293B",
        "input_bg": "#1E293B",
        "input_focus_bg": "#253049",
        "progress_bg": "#2D3B55",
        "menu_hover": "#1E293B"
    },
    "emerald_zinc": {
        "label": "Emerald & Zinc",
        "description": "Natural, grounded, low eye strain \u2014 GitHub dark style.",
        "bg_primary": "#0D1117",
        "bg_surface": "#161B22",
        "bg_elevated": "#21262D",
        "bg_interactive": "#2D333B",
        "bg_hover": "#30363D",
        "border": "#30363D",
        "border_light": "#484F58",
        "border_dark": "#5B636F",
        "text_primary": "#F0F6FC",
        "text_secondary": "#8B949E",
        "text_tertiary": "#6E7681",
        "text_disabled": "#484F58",
        "text_highlight": "#E6EDF3",
        "text_white": "#FFFFFF",
        "primary": "#34D399",
        "primary_hover": "#6EE7B7",
        "primary_pressed": "#10B981",
        "accent": "#34D399",
        "accent_hover": "#6EE7B7",
        "accent_pressed": "#10B981",
        "accent_text": "#0D1117",
        "destructive": "#30363D",
        "destructive_hover": "#484F58",
        "status_success": "#34D399",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#58A6FF",
        "scrollbar": "#30363D",
        "scrollbar_hover": "#484F58",
        "scrollbar_bg": "#0D1117",
        "selection": "#161B22",
        "focus": "#34D399",
        "tab_selected_border": "#34D399",
        "tab_hover": "#21262D",
        "input_bg": "#21262D",
        "input_focus_bg": "#262C36",
        "progress_bg": "#30363D",
        "menu_hover": "#21262D"
    },
    "amber_zinc": {
        "label": "Amber & Zinc",
        "description": "Warm, approachable \u2014 refined version of the current yellow.",
        "bg_primary": "#0F0F0F",
        "bg_surface": "#1A1A1A",
        "bg_elevated": "#262626",
        "bg_interactive": "#323232",
        "bg_hover": "#3A3A3A",
        "border": "#3F3F3F",
        "border_light": "#525252",
        "border_dark": "#666666",
        "text_primary": "#FAFAF9",
        "text_secondary": "#A8A29E",
        "text_tertiary": "#78716C",
        "text_disabled": "#525252",
        "text_highlight": "#F5F5F4",
        "text_white": "#FFFFFF",
        "primary": "#FBBF24",
        "primary_hover": "#FCD34D",
        "primary_pressed": "#F59E0B",
        "accent": "#FBBF24",
        "accent_hover": "#FCD34D",
        "accent_pressed": "#F59E0B",
        "accent_text": "#0F0F0F",
        "destructive": "#3A3A3A",
        "destructive_hover": "#525252",
        "status_success": "#4ADE80",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#60A5FA",
        "scrollbar": "#3F3F3F",
        "scrollbar_hover": "#525252",
        "scrollbar_bg": "#0F0F0F",
        "selection": "#1A1A1A",
        "focus": "#FBBF24",
        "tab_selected_border": "#FBBF24",
        "tab_hover": "#262626",
        "input_bg": "#262626",
        "input_focus_bg": "#2E2E2E",
        "progress_bg": "#3F3F3F",
        "menu_hover": "#262626"
    },
    "violet_neutral": {
        "label": "Violet & Neutral",
        "description": "Creative, distinctive, premium feel.",
        "bg_primary": "#0C0A19",
        "bg_surface": "#1E1B4B",
        "bg_elevated": "#312E81",
        "bg_interactive": "#3735A3",
        "bg_hover": "#4338CA",
        "border": "#312E81",
        "border_light": "#4338CA",
        "border_dark": "#5B50E0",
        "text_primary": "#F8FAFC",
        "text_secondary": "#9CA3AF",
        "text_tertiary": "#6B7280",
        "text_disabled": "#4338CA",
        "text_highlight": "#F1F5FB",
        "text_white": "#FFFFFF",
        "primary": "#818CF8",
        "primary_hover": "#A5B4FC",
        "primary_pressed": "#6366F1",
        "accent": "#C084FC",
        "accent_hover": "#D8B4FE",
        "accent_pressed": "#A855F7",
        "accent_text": "#0C0A19",
        "destructive": "#4338CA",
        "destructive_hover": "#5B50E0",
        "status_success": "#4ADE80",
        "status_warning": "#FBBF24",
        "status_error": "#F87171",
        "status_info": "#60A5FA",
        "scrollbar": "#4338CA",
        "scrollbar_hover": "#5B50E0",
        "scrollbar_bg": "#0C0A19",
        "selection": "#3730A3",
        "focus": "#818CF8",
        "tab_selected_border": "#818CF8",
        "tab_hover": "#312E81",
        "input_bg": "#312E81",
        "input_focus_bg": "#3735A3",
        "progress_bg": "#4338CA",
        "menu_hover": "#312E81"
    }
}


@dataclass(frozen=True)
class Theme:
    """A color theme for the application."""

    name: str
    label: str
    description: str
    palette: dict[str, str]

    def get(self, key: str, default: str = "#000000") -> str:
        """Get a color from this theme's palette."""
        return self.palette.get(key, default)


THEMES: list[Theme] = []
THEMES.append(
    Theme(
        name="modern_dark",
        label="Modern Dark",
        description="The current purple-yellow-dark scheme.",
        palette=_THEME_PALETTES["modern_dark"],
    )
)
THEMES.append(
    Theme(
        name="slate_sky",
        label="Slate & Sky",
        description="Calm, professional \u2014 like Linear and Notion.",
        palette=_THEME_PALETTES["slate_sky"],
    )
)
THEMES.append(
    Theme(
        name="indigo_cyan",
        label="Indigo & Cyan",
        description="Sharp, intelligent, tech-forward \u2014 signals AI-powered.",
        palette=_THEME_PALETTES["indigo_cyan"],
    )
)
THEMES.append(
    Theme(
        name="emerald_zinc",
        label="Emerald & Zinc",
        description="Natural, grounded, low eye strain \u2014 GitHub dark style.",
        palette=_THEME_PALETTES["emerald_zinc"],
    )
)
THEMES.append(
    Theme(
        name="amber_zinc",
        label="Amber & Zinc",
        description="Warm, approachable \u2014 refined version of the current yellow.",
        palette=_THEME_PALETTES["amber_zinc"],
    )
)
THEMES.append(
    Theme(
        name="violet_neutral",
        label="Violet & Neutral",
        description="Creative, distinctive, premium feel.",
        palette=_THEME_PALETTES["violet_neutral"],
    )
)


DEFAULT_THEME_NAME = "modern_dark"
THEME_BY_NAME: dict[str, Theme] = {t.name: t for t in THEMES}


def get_theme(name: str) -> Theme:
    """Get a theme by name, falling back to the default."""
    theme = THEME_BY_NAME.get(name)
    if theme is not None:
        return theme
    logger.warning("Unknown theme %r, falling back to %s", name, DEFAULT_THEME_NAME)
    return THEME_BY_NAME[DEFAULT_THEME_NAME]


_TOKENS_IN_TEMPLATE: list[str] = [
    "accent_hover",
    "accent_pressed",
    "bg_hover",
    "bg_surface",
    "input_bg",
    "input_focus_bg",
    "menu_hover",
    "primary_hover",
    "primary_pressed",
    "progress_bg",
    "scrollbar",
    "scrollbar_bg",
    "scrollbar_hover",
    "status_error",
    "status_info",
    "status_success",
    "status_warning",
    "tab_selected_border",
    "text_disabled",
    "text_highlight",
    "text_primary",
    "text_secondary",
    "text_tertiary",
    "text_white"
]


_QSS_TEMPLATE: str = '\n\nDARK_THEME = """\n/* ============================================\n   DESIGN TOKENS\n   ============================================ */\n/*\n   Background hierarchy:\n   - Surface 0 (deepest): {scrollbar_bg} - App background\n   - Surface 1 (base): {bg_surface} - Main panels\n   - Surface 2 (elevated): {input_bg} - Cards, grouped sections\n   - Surface 3 (interactive): {menu_hover} - Buttons, inputs\n\n   Text hierarchy:\n   - Primary: {text_primary} - Headings, important text\n   - Secondary: {text_secondary} - Labels, descriptions\n   - Tertiary: {text_tertiary} - Placeholders, disabled\n   - Accent: {tab_selected_border} - Primary action color\n\n   Status colors:\n   - Success: {status_success}\n   - Warning: {status_warning}\n   - Error: {status_error}\n   - Info: {status_info}\n*/\n\n/* ============================================\n   MAIN WINDOW\n   ============================================ */\nQMainWindow {\n    background-color: {scrollbar_bg};\n}\n\n/* ============================================\n   MENU BAR\n   ============================================ */\nQMenuBar {\n    background-color: {bg_surface};\n    color: {text_secondary};\n    border-bottom: 1px solid {progress_bg};\n    padding: 4px 0;\n}\n\nQMenuBar::item {\n    padding: 6px 12px;\n    background-color: transparent;\n    border-radius: 4px;\n    margin: 2px 4px;\n}\n\nQMenuBar::item:selected {\n    background-color: {menu_hover};\n    color: {text_primary};\n}\n\n/* ============================================\n   MENUS\n   ============================================ */\nQMenu {\n    background-color: {input_bg};\n    color: {text_secondary};\n    border: 1px solid {progress_bg};\n    border-radius: 8px;\n    padding: 6px 0;\n    margin: 4px;\n}\n\nQMenu::item {\n    padding: 8px 32px 8px 16px;\n    border-radius: 4px;\n    margin: 2px 8px;\n}\n\nQMenu::item:selected {\n    background-color: {menu_hover};\n    color: {text_primary};\n}\n\nQMenu::separator {\n    height: 1px;\n    background-color: {progress_bg};\n    margin: 6px 12px;\n}\n\n/* ============================================\n   BUTTONS\n   ============================================ */\nQPushButton {\n    background-color: {menu_hover};\n    color: {text_secondary};\n    border: 1px solid {scrollbar};\n    padding: 8px 16px;\n    border-radius: 8px;\n    font-size: 13px;\n    font-weight: 500;\n    min-height: 36px;\n}\n\nQPushButton:hover {\n    background-color: {bg_hover};\n    border-color: {scrollbar_hover};\n    color: palette(windowtext);\n}\n\nQPushButton:pressed {\n    background-color: {tab_selected_border};\n    border-color: palette(highlight);\n    color: {text_white};\n}\n\nQPushButton:disabled {\n    background-color: {bg_surface};\n    color: {text_tertiary};\n    border-color: {progress_bg};\n}\n\n/* Record button - Primary action */\nQPushButton#recordButton {\n    background-color: {tab_selected_border};\n    border-color: {tab_selected_border};\n    color: {text_white};\n    font-weight: 600;\n}\n\nQPushButton#recordButton:hover {\n    background-color: {primary_hover};\n    border-color: {primary_hover};\n}\n\nQPushButton#recordButton:pressed {\n    background-color: {primary_pressed};\n    border-color: {primary_pressed};\n}\n\nQPushButton#recordButton:disabled {\n    background-color: {progress_bg};\n    border-color: {scrollbar};\n    color: {text_disabled};\n}\n\n/* Pause button - Secondary action */\nQPushButton#pauseButton {\n    background-color: {accent};\n    border-color: {accent};\n    color: {accent_text};\n    font-weight: 600;\n}\n\nQPushButton#pauseButton:hover {\n    background-color: {accent_hover};\n    border-color: {accent_hover};\n}\n\nQPushButton#pauseButton:pressed {\n    background-color: {accent_pressed};\n    border-color: {accent_pressed};\n}\n\n/* Stop button - Destructive action */\nQPushButton#stopButton {\n    background-color: {destructive};\n    border-color: {destructive_hover};\n    color: {text_secondary};\n}\n\nQPushButton#stopButton:hover {\n    background-color: {destructive_hover};\n    border-color: {destructive};\n    color: {text_primary};\n}\n\n/* ============================================\n   LABELS\n   ============================================ */\nQLabel {\n    color: {text_secondary};\n    font-size: 13px;\n}\n\nQLabel#title {\n    font-size: 18px;\n    font-weight: 600;\n    color: {text_primary};\n    letter-spacing: -0.3px;\n}\n\nQLabel#statusLabel {\n    font-size: 12px;\n    color: {text_tertiary};\n}\n\n/* ============================================\n   TEXT EDITS AND DISPLAYS\n   ============================================ */\nQTextEdit, QPlainTextEdit {\n    background-color: {input_bg};\n    color: {text_highlight};\n    border: 1px solid {progress_bg};\n    border-radius: 8px;\n    padding: 12px;\n    font-family: \'SF Mono\', \'Monaco\', \'Consolas\', monospace;\n    font-size: 13px;\n    line-height: 1.6;\n}\n\nQTextEdit:focus, QPlainTextEdit:focus {\n    border-color: {tab_selected_border};\n    background-color: {input_focus_bg};\n}\n\nQTextEdit::placeholder, QPlainTextEdit::placeholder {\n    color: {text_disabled};\n}\n\n/* ============================================\n   SLIDERS\n   ============================================ */\nQSlider::groove:horizontal {\n    background: {progress_bg};\n    height: 6px;\n    border-radius: 3px;\n}\n\nQSlider::handle:horizontal {\n    background: {tab_selected_border};\n    width: 18px;\n    margin: -6px 0;\n    border-radius: 9px;\n}\n\nQSlider::handle:horizontal:hover {\n    background: {primary_hover};\n}\n\nQSlider::handle:horizontal:pressed {\n    background: {primary_pressed};\n}\n\nQSlider::sub-page:horizontal {\n    background: {tab_selected_border};\n    border-radius: 3px;\n}\n\n/* ============================================\n   GROUP BOXES\n   ============================================ */\nQGroupBox {\n    background-color: {input_bg};\n    border: 1px solid {progress_bg};\n    border-radius: 10px;\n    margin-top: 10px;\n    padding-top: 14px;\n    font-weight: 600;\n    color: {text_primary};\n    font-size: 14px;\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n    left: 14px;\n    padding: 0 6px;\n    color: {text_primary};\n}\n\n/* ============================================\n   COMBO BOX\n   ============================================ */\nQComboBox {\n    background-color: {input_bg};\n    color: {text_secondary};\n    border: 1px solid {progress_bg};\n    border-radius: 8px;\n    padding: 6px 12px;\n    min-width: 140px;\n    font-size: 13px;\n}\n\nQComboBox:hover {\n    border-color: {tab_selected_border};\n}\n\nQComboBox::drop-down {\n    border: none;\n    width: 24px;\n}\n\nQComboBox::down-arrow {\n    image: none;\n    border-left: 4px solid transparent;\n    border-right: 4px solid transparent;\n    border-top: 6px solid {text_tertiary};\n    margin-right: 8px;\n}\n\nQComboBox QAbstractItemView {\n    background-color: {input_bg};\n    color: {text_secondary};\n    selection-background-color: {menu_hover};\n    selection-color: {text_primary};\n    border: 1px solid {progress_bg};\n    border-radius: 8px;\n    outline: none;\n    padding: 4px;\n}\n\nQComboBox QAbstractItemView::item {\n    padding: 8px 12px;\n    border-radius: 4px;\n    margin: 2px 4px;\n}\n\nQComboBox QAbstractItemView::item:selected {\n    background-color: {menu_hover};\n    color: {text_primary};\n}\n\n/* ============================================\n   LINE EDITS\n   ============================================ */\nQLineEdit {\n    background-color: {input_bg};\n    color: {text_highlight};\n    border: 1px solid {progress_bg};\n    border-radius: 8px;\n    padding: 6px 12px;\n    font-size: 13px;\n}\n\nQLineEdit:focus {\n    border-color: {tab_selected_border};\n    background-color: {input_focus_bg};\n}\n\nQLineEdit:disabled {\n    background-color: {bg_surface};\n    color: {text_disabled};\n}\n\n/* ============================================\n   SCROLL BARS\n   ============================================ */\nQScrollBar:vertical {\n    background-color: {scrollbar_bg};\n    width: 10px;\n    border-radius: 5px;\n    margin: 0;\n}\n\nQScrollBar::handle:vertical {\n    background-color: {scrollbar};\n    border-radius: 5px;\n    min-height: 24px;\n}\n\nQScrollBar::handle:vertical:hover {\n    background-color: {scrollbar_hover};\n}\n\nQScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n    height: 0px;\n}\n\nQScrollBar:horizontal {\n    background-color: {scrollbar_bg};\n    height: 10px;\n    border-radius: 5px;\n    margin: 0;\n}\n\nQScrollBar::handle:horizontal {\n    background-color: {scrollbar};\n    border-radius: 5px;\n    min-width: 24px;\n}\n\nQScrollBar::handle:horizontal:hover {\n    background-color: {scrollbar_hover};\n}\n\n/* ============================================\n   PROGRESS BAR\n   ============================================ */\nQProgressBar {\n    background-color: {progress_bg};\n    border: 1px solid {scrollbar};\n    border-radius: 6px;\n    text-align: center;\n    color: {text_secondary};\n    height: 22px;\n    font-size: 12px;\n}\n\nQProgressBar::chunk {\n    background-color: {tab_selected_border};\n    border-radius: 5px;\n}\n\n/* ============================================\n   STATUS BAR\n   ============================================ */\nQStatusBar {\n    background-color: {bg_surface};\n    color: {text_tertiary};\n    border-top: 1px solid {progress_bg};\n    font-size: 12px;\n}\n\n/* ============================================\n   TABS\n   ============================================ */\nQTabWidget::pane {\n    border: 1px solid {progress_bg};\n    background-color: {input_bg};\n    border-radius: 10px;\n}\n\nQTabBar::tab {\n    background-color: {bg_surface};\n    color: {text_tertiary};\n    padding: 10px 20px;\n    border-top-left-radius: 8px;\n    border-top-right-radius: 8px;\n    font-size: 13px;\n    font-weight: 500;\n    margin-right: 2px;\n}\n\nQTabBar::tab:selected {\n    background-color: {input_bg};\n    color: {text_primary};\n    border-bottom: 2px solid {tab_selected_border};\n}\n\nQTabBar::tab:hover {\n    background-color: {input_focus_bg};\n    color: {text_secondary};\n}\n\n/* ============================================\n   CHECKBOX\n   ============================================ */\nQCheckBox {\n    color: {text_secondary};\n    spacing: 10px;\n    font-size: 13px;\n}\n\nQCheckBox::indicator {\n    width: 18px;\n    height: 18px;\n    border: 2px solid {scrollbar};\n    border-radius: 4px;\n    background-color: {input_bg};\n}\n\nQCheckBox::indicator:hover {\n    border-color: {tab_selected_border};\n}\n\nQCheckBox::indicator:checked {\n    background-color: {tab_selected_border};\n    border-color: {tab_selected_border};\n}\n\n/* ============================================\n   FRAME\n   ============================================ */\nQFrame {\n    border-radius: 8px;\n}\n\nQFrame#raised {\n    background-color: {input_bg};\n    border: 1px solid {progress_bg};\n}\n'


def apply_theme(app, theme_name: str = DEFAULT_THEME_NAME):
    """Apply a theme by name to the Qt application.

    Replaces the color tokens in the QSS stylesheet with
    the selected theme's colors and sets it on the app.
    Also sets a QPalette so native Qt controls (combo boxes,
    checkboxes, line edits, buttons, etc.) follow the theme.
    """
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt

    theme = get_theme(theme_name)
    p = theme.palette

    # --- QSS ---------------------------------------------------------------
    qss = _QSS_TEMPLATE
    for token in _TOKENS_IN_TEMPLATE:
        color = p.get(token)
        if color:
            qss = qss.replace("{" + token + "}", color)
        else:
            logger.warning("Missing color for token %r in theme %s", token, theme.name)

    app.setStyleSheet(qss)

    # --- QPalette for native controls --------------------------------------
    qpal = QPalette()

    # Backgrounds
    qpal.setColor(QPalette.Window, QColor(p["bg_primary"]))
    qpal.setColor(QPalette.WindowText, QColor(p["text_primary"]))
    qpal.setColor(QPalette.Base, QColor(p["input_bg"]))
    qpal.setColor(QPalette.AlternateBase, QColor(p["bg_hover"]))
    qpal.setColor(QPalette.ToolTipBase, QColor(p["bg_elevated"]))
    qpal.setColor(QPalette.ToolTipText, QColor(p["text_primary"]))
    qpal.setColor(QPalette.Text, QColor(p["text_primary"]))
    qpal.setColor(QPalette.Button, QColor(p["bg_interactive"]))
    qpal.setColor(QPalette.ButtonText, QColor(p["text_secondary"]))

    # Highlights / selection
    qpal.setColor(QPalette.BrightText, QColor(p["accent"]))
    qpal.setColor(QPalette.Link, QColor(p["primary"]))
    qpal.setColor(QPalette.LinkVisited, QColor(p["primary_hover"]))
    qpal.setColor(QPalette.Highlight, QColor(p["primary"]))
    qpal.setColor(QPalette.HighlightedText, QColor(p["accent_text"]))

    # Disabled
    qpal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(p["text_tertiary"]))
    qpal.setColor(QPalette.Disabled, QPalette.Text, QColor(p["text_tertiary"]))
    qpal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(p["text_tertiary"]))
    qpal.setColor(QPalette.Disabled, QPalette.Window, QColor(p["bg_surface"]))
    qpal.setColor(QPalette.Disabled, QPalette.Base, QColor(p["bg_surface"]))

    # Placeholder text (line edits)
    qpal.setColor(QPalette.PlaceholderText, QColor(p["text_tertiary"]))

    # Shadow (used for dialog backgrounds, etc.)
    qpal.setColor(QPalette.Shadow, QColor(p["border"]))

    app.setPalette(qpal)

    logger.info("Applied theme: %s (%s)", theme.label, theme.name)

