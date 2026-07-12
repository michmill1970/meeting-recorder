"""Modern dark theme stylesheet for the application.

Based on 2025 UI/UX design principles:
- Dark grays instead of pure black (Figma #1E1E1E, YouTube #181818, Slack #1D1D1D)
- Off-white text (#E0E0E0) instead of pure white for reduced eye strain
- Limited color palette with 1-2 accent colors
- Larger rounded corners for modern feel
- Spacious layouts with clear visual hierarchy
- WCAG AA compliant contrast ratios
- Micro-interactions (hover, press, focus states)
"""

DARK_THEME = """
/* ============================================
   DESIGN TOKENS
   ============================================ */
/*
   Background hierarchy:
   - Surface 0 (deepest): #0A0A0F - App background
   - Surface 1 (base): #12121A - Main panels
   - Surface 2 (elevated): #1A1A26 - Cards, grouped sections
   - Surface 3 (interactive): #24243A - Buttons, inputs

   Text hierarchy:
   - Primary: #E8E8ED - Headings, important text
   - Secondary: #A0A0B0 - Labels, descriptions
   - Tertiary: #6E6E7A - Placeholders, disabled
   - Accent: #6C63FF - Primary action color

   Status colors:
   - Success: #4ADE80
   - Warning: #FBBF24
   - Error: #F87171
   - Info: #60A5FA
*/

/* ============================================
   MAIN WINDOW
   ============================================ */
QMainWindow {
    background-color: #0A0A0F;
}

/* ============================================
   MENU BAR
   ============================================ */
QMenuBar {
    background-color: #12121A;
    color: #A0A0B0;
    border-bottom: 1px solid #2A2A3A;
    padding: 4px 0;
}

QMenuBar::item {
    padding: 6px 12px;
    background-color: transparent;
    border-radius: 4px;
    margin: 2px 4px;
}

QMenuBar::item:selected {
    background-color: #24243A;
    color: #E8E8ED;
}

/* ============================================
   MENUS
   ============================================ */
QMenu {
    background-color: #1A1A26;
    color: #A0A0B0;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    padding: 6px 0;
    margin: 4px;
}

QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
    margin: 2px 8px;
}

QMenu::item:selected {
    background-color: #24243A;
    color: #E8E8ED;
}

QMenu::separator {
    height: 1px;
    background-color: #2A2A3A;
    margin: 6px 12px;
}

/* ============================================
   BUTTONS
   ============================================ */
QPushButton {
    background-color: #24243A;
    color: #A0A0B0;
    border: 1px solid #3A3A5A;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    min-height: 36px;
}

QPushButton:hover {
    background-color: #2A2A42;
    border-color: #4A4A6A;
    color: #E8E8ED;
}

QPushButton:pressed {
    background-color: #6C63FF;
    border-color: #6C63FF;
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: #1A1A26;
    color: #4A4A5A;
    border-color: #2A2A3A;
}

/* Record button - Primary action */
QPushButton#recordButton {
    background-color: #6C63FF;
    border-color: #6C63FF;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#recordButton:hover {
    background-color: #7B73FF;
    border-color: #7B73FF;
}

QPushButton#recordButton:pressed {
    background-color: #5B52EE;
    border-color: #5B52EE;
}

QPushButton#recordButton:disabled {
    background-color: #2A2A3A;
    border-color: #3A3A5A;
    color: #4A4A5A;
}

/* Pause button - Secondary action */
QPushButton#pauseButton {
    background-color: #FBBF24;
    border-color: #FBBF24;
    color: #0A0A0F;
    font-weight: 600;
}

QPushButton#pauseButton:hover {
    background-color: #FCD34D;
    border-color: #FCD34D;
}

QPushButton#pauseButton:pressed {
    background-color: #F59E0B;
    border-color: #F59E0B;
}

/* Stop button - Destructive action */
QPushButton#stopButton {
    background-color: #3A3A5A;
    border-color: #4A4A6A;
    color: #A0A0B0;
}

QPushButton#stopButton:hover {
    background-color: #4A4A6A;
    border-color: #5A5A7A;
    color: #E8E8ED;
}

/* ============================================
   LABELS
   ============================================ */
QLabel {
    color: #A0A0B0;
    font-size: 13px;
}

QLabel#title {
    font-size: 18px;
    font-weight: 600;
    color: #E8E8ED;
    letter-spacing: -0.3px;
}

QLabel#statusLabel {
    font-size: 12px;
    color: #6E6E7A;
}

/* ============================================
   TEXT EDITS AND DISPLAYS
   ============================================ */
QTextEdit, QPlainTextEdit {
    background-color: #1A1A26;
    color: #E0E0E5;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    padding: 12px;
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #6C63FF;
    background-color: #1E1E2A;
}

QTextEdit::placeholder, QPlainTextEdit::placeholder {
    color: #4A4A5A;
}

/* ============================================
   SLIDERS
   ============================================ */
QSlider::groove:horizontal {
    background: #2A2A3A;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #6C63FF;
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #7B73FF;
}

QSlider::handle:horizontal:pressed {
    background: #5B52EE;
}

QSlider::sub-page:horizontal {
    background: #6C63FF;
    border-radius: 3px;
}

/* ============================================
   GROUP BOXES
   ============================================ */
QGroupBox {
    background-color: #1A1A26;
    border: 1px solid #2A2A3A;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: 600;
    color: #E8E8ED;
    font-size: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #E8E8ED;
}

/* ============================================
   COMBO BOX
   ============================================ */
QComboBox {
    background-color: #1A1A26;
    color: #A0A0B0;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 140px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #6C63FF;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #6E6E7A;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1A1A26;
    color: #A0A0B0;
    selection-background-color: #24243A;
    selection-color: #E8E8ED;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #24243A;
    color: #E8E8ED;
}

/* ============================================
   LINE EDITS
   ============================================ */
QLineEdit {
    background-color: #1A1A26;
    color: #E0E0E5;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #6C63FF;
    background-color: #1E1E2A;
}

QLineEdit:disabled {
    background-color: #12121A;
    color: #4A4A5A;
}

/* ============================================
   SCROLL BARS
   ============================================ */
QScrollBar:vertical {
    background-color: #0A0A0F;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3A3A5A;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4A4A6A;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0A0A0F;
    height: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3A3A5A;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4A4A6A;
}

/* ============================================
   PROGRESS BAR
   ============================================ */
QProgressBar {
    background-color: #2A2A3A;
    border: 1px solid #3A3A5A;
    border-radius: 6px;
    text-align: center;
    color: #A0A0B0;
    height: 22px;
    font-size: 12px;
}

QProgressBar::chunk {
    background-color: #6C63FF;
    border-radius: 5px;
}

/* ============================================
   STATUS BAR
   ============================================ */
QStatusBar {
    background-color: #12121A;
    color: #6E6E7A;
    border-top: 1px solid #2A2A3A;
    font-size: 12px;
}

/* ============================================
   TABS
   ============================================ */
QTabWidget::pane {
    border: 1px solid #2A2A3A;
    background-color: #1A1A26;
    border-radius: 10px;
}

QTabBar::tab {
    background-color: #12121A;
    color: #6E6E7A;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1A1A26;
    color: #E8E8ED;
    border-bottom: 2px solid #6C63FF;
}

QTabBar::tab:hover {
    background-color: #1E1E2A;
    color: #A0A0B0;
}

/* ============================================
   CHECKBOX
   ============================================ */
QCheckBox {
    color: #A0A0B0;
    spacing: 10px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #3A3A5A;
    border-radius: 4px;
    background-color: #1A1A26;
}

QCheckBox::indicator:hover {
    border-color: #6C63FF;
}

QCheckBox::indicator:checked {
    background-color: #6C63FF;
    border-color: #6C63FF;
}

/* ============================================
   FRAME
   ============================================ */
QFrame {
    border-radius: 8px;
}

QFrame#raised {
    background-color: #1A1A26;
    border: 1px solid #2A2A3A;
}
"""
