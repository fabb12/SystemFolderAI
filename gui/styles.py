"""
gui/styles.py — Tema dark mode moderno (QSS)
"""

# Palette: ispirata a Tokyo Night / VS Code Dark+
COLORS = {
    "bg":          "#1a1b26",
    "bg_alt":      "#1f2030",
    "bg_panel":    "#24283b",
    "bg_hover":    "#2f3447",
    "bg_input":    "#16161e",
    "border":      "#2d3142",
    "border_soft": "#33384d",
    "text":        "#c0caf5",
    "text_dim":    "#9aa5ce",
    "text_muted":  "#565f89",
    "accent":      "#7aa2f7",
    "accent_hov":  "#89b4fa",
    "success":     "#9ece6a",
    "warning":     "#e0af68",
    "error":       "#f7768e",
    "purple":      "#bb9af7",
    "cyan":        "#7dcfff",
}


def dark_qss() -> str:
    c = COLORS
    return f"""
    /* ── Base ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: 'Segoe UI', 'SF Pro Text', 'Inter', sans-serif;
        font-size: 13px;
    }}

    QMainWindow, QDialog {{
        background-color: {c['bg']};
    }}

    /* ── Sidebar ──────────────────────────────────────────── */
    #Sidebar {{
        background-color: {c['bg_alt']};
        border-right: 1px solid {c['border']};
    }}

    #SidebarTitle {{
        color: {c['accent']};
        font-size: 18px;
        font-weight: 700;
        padding: 18px 16px 6px 16px;
    }}

    #SidebarSubtitle {{
        color: {c['text_muted']};
        font-size: 11px;
        padding: 0 16px 18px 16px;
    }}

    #SidebarLabel {{
        color: {c['text_muted']};
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 14px 16px 4px 16px;
    }}

    QPushButton#SidebarBtn {{
        background-color: transparent;
        color: {c['text']};
        border: none;
        border-radius: 6px;
        padding: 9px 14px;
        text-align: left;
        font-size: 13px;
        margin: 1px 8px;
    }}
    QPushButton#SidebarBtn:hover {{
        background-color: {c['bg_hover']};
    }}
    QPushButton#SidebarBtn:pressed {{
        background-color: {c['bg_panel']};
    }}
    QPushButton#SidebarBtn:checked {{
        background-color: {c['accent']};
        color: {c['bg']};
        font-weight: 600;
    }}

    /* ── Topbar ───────────────────────────────────────────── */
    #Topbar {{
        background-color: {c['bg_alt']};
        border-bottom: 1px solid {c['border']};
    }}
    #TopbarLabel {{
        color: {c['text_dim']};
        font-size: 12px;
    }}
    #ModelPill {{
        background-color: {c['bg_panel']};
        color: {c['cyan']};
        border: 1px solid {c['border_soft']};
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
    }}

    /* ── Buttons ──────────────────────────────────────────── */
    QPushButton {{
        background-color: {c['bg_panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 7px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['border_soft']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_alt']};
    }}
    QPushButton:disabled {{
        color: {c['text_muted']};
        background-color: {c['bg_alt']};
    }}

    QPushButton#PrimaryBtn {{
        background-color: {c['accent']};
        color: {c['bg']};
        border: none;
        font-weight: 600;
    }}
    QPushButton#PrimaryBtn:hover {{
        background-color: {c['accent_hov']};
    }}
    QPushButton#PrimaryBtn:disabled {{
        background-color: {c['bg_panel']};
        color: {c['text_muted']};
    }}

    QPushButton#DangerBtn {{
        background-color: transparent;
        color: {c['error']};
        border: 1px solid {c['error']};
    }}
    QPushButton#DangerBtn:hover {{
        background-color: {c['error']};
        color: {c['bg']};
    }}

    /* ── Inputs ───────────────────────────────────────────── */
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 7px 10px;
        selection-background-color: {c['accent']};
        selection-color: {c['bg']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['accent']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c['text_dim']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_panel']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
        selection-color: {c['bg']};
        outline: none;
    }}

    /* ── Chat output ──────────────────────────────────────── */
    #ChatView {{
        background-color: {c['bg']};
        border: none;
        padding: 12px 16px;
    }}

    /* ── Input bar ────────────────────────────────────────── */
    #InputBar {{
        background-color: {c['bg_alt']};
        border-top: 1px solid {c['border']};
    }}
    #InputField {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 13px;
    }}
    #InputField:focus {{
        border-color: {c['accent']};
    }}

    /* ── Labels ───────────────────────────────────────────── */
    QLabel {{
        background: transparent;
        color: {c['text']};
    }}
    QLabel#FormLabel {{
        color: {c['text_dim']};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#HelpText {{
        color: {c['text_muted']};
        font-size: 11px;
    }}
    QLabel#SectionHeader {{
        color: {c['accent']};
        font-size: 14px;
        font-weight: 700;
        padding: 6px 0 2px 0;
    }}

    /* ── Tabs ─────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 6px;
        background-color: {c['bg_alt']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_dim']};
        padding: 8px 16px;
        border: 1px solid transparent;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['bg_alt']};
        color: {c['accent']};
        border-color: {c['border']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {c['text']};
    }}

    /* ── Scrollbars ───────────────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border_soft']};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border_soft']};
        border-radius: 4px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── Checkbox ─────────────────────────────────────────── */
    QCheckBox {{
        spacing: 8px;
        color: {c['text']};
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {c['border_soft']};
        border-radius: 4px;
        background: {c['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ── Status bar ───────────────────────────────────────── */
    QStatusBar {{
        background-color: {c['bg_alt']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* ── Menu ─────────────────────────────────────────────── */
    QMenuBar {{
        background-color: {c['bg_alt']};
        color: {c['text']};
        border-bottom: 1px solid {c['border']};
    }}
    QMenuBar::item:selected {{
        background-color: {c['bg_hover']};
    }}
    QMenu {{
        background-color: {c['bg_panel']};
        border: 1px solid {c['border']};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 22px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {c['accent']};
        color: {c['bg']};
    }}

    /* ── Tooltip ──────────────────────────────────────────── */
    QToolTip {{
        background-color: {c['bg_panel']};
        color: {c['text']};
        border: 1px solid {c['border_soft']};
        padding: 5px 8px;
        border-radius: 4px;
    }}

    /* ── Splitter ─────────────────────────────────────────── */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical   {{ height: 1px; }}

    /* ── Group box ────────────────────────────────────────── */
    QGroupBox {{
        background-color: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        margin-top: 14px;
        padding: 12px;
        color: {c['text']};
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {c['accent']};
    }}
    """
