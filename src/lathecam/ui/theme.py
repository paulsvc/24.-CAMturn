from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

_CURRENT_THEME: str = "dark"

# Default CAD Viewport Color Palette (Dark Mode)
VIEWPORT_BG_TOP = "#141820"
VIEWPORT_BG_BOTTOM = "#222936"
STOCK_MESH_COLOR = "#38bdf8"      # Translucent sky blue stock cylinder
PART_MESH_COLOR = "#94a3b8"       # Machined steel metallic silver-slate
CUT_STOCK_COLOR = "#64748b"       # Simulated cut stock
SHADOW_POLY_COLOR = "#f59e0b"     # Amber undercut shadow overlay
GOUGE_POLY_COLOR = "#ef4444"      # Bright red gouge alert
REST_POLY_COLOR = "#3b82f6"       # Blue uncut rest material

# Toolpath Wireframe Colors
COLOR_RAPID_G0 = "#ef4444"        # Red rapid moves
COLOR_CUT_G1 = "#16a34a"          # Green linear cuts
COLOR_ARC_G2_G3 = "#0891b2"       # Cyan circular arc moves
COLOR_THREAD_G33 = "#ca8a04"      # Gold/amber synchronized thread passes


def get_current_theme() -> str:
    """Returns the currently active theme ('dark' or 'light')."""
    return _CURRENT_THEME


def get_viewport_colors(mode: str | None = None) -> dict[str, str]:
    """Returns theme-adapted colors for the VTK 3D/2D viewport and HUD."""
    theme = mode or _CURRENT_THEME
    if theme == "light":
        return {
            "bg_top": "#dbeafe",
            "bg_bottom": "#f8fafc",
            "hud_bg": "#f1f5f9",
            "hud_border": "#cbd5e1",
            "profile_line": "#0f172a",
            "stock_wire": "#0284c7",
            "centerline": "#64748b",
            "axes_color": "#0f172a",
            "part_mesh": "#64748b",
            "stock_mesh": "#0ea5e9",
            "sim_mesh": "#0284c7",
            "g0": "#dc2626",
            "g1": "#15803d",
            "arc": "#0369a1",
            "thread": "#b45309",
        }
    return {
        "bg_top": VIEWPORT_BG_TOP,
        "bg_bottom": VIEWPORT_BG_BOTTOM,
        "hud_bg": "#1a202c",
        "hud_border": "#2d3748",
        "profile_line": "#f8fafc",
        "stock_wire": "#38bdf8",
        "centerline": "#64748b",
        "axes_color": "#f8fafc",
        "part_mesh": PART_MESH_COLOR,
        "stock_mesh": STOCK_MESH_COLOR,
        "sim_mesh": "#38bdf8",
        "g0": "#ef4444",
        "g1": "#22c55e",
        "arc": "#06b6d4",
        "thread": "#eab308",
    }


DARK_CAD_STYLESHEET = """
QMainWindow {
    background-color: #161920;
    color: #e2e8f0;
}

QMenuBar {
    background-color: #1a1e26;
    color: #cbd5e1;
    border-bottom: 1px solid #2d3545;
    padding: 2px;
    font-size: 12px;
}

QMenuBar::item:selected {
    background-color: #2d3748;
    border-radius: 4px;
}

QMenu {
    background-color: #1e2430;
    color: #e2e8f0;
    border: 1px solid #334155;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QToolBar {
    background-color: #1e232d;
    border-bottom: 1px solid #2e3646;
    spacing: 4px;
    padding: 4px 6px;
}

QToolButton {
    background-color: #262d3b;
    color: #e2e8f0;
    border: 1px solid #364154;
    border-radius: 5px;
    padding: 4px 7px;
    font-weight: 600;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #323c4f;
    border-color: #3b82f6;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #2563eb;
    border-color: #60a5fa;
    color: #ffffff;
}

QDockWidget {
    color: #f1f5f9;
    font-weight: bold;
    font-size: 12px;
    titlebar-close-icon: url(none);
}

QDockWidget::title {
    background-color: #232936;
    border-top: 1px solid #334155;
    border-bottom: 1px solid #2d3748;
    padding: 7px 10px;
    text-align: left;
}

QTreeWidget, QTableWidget, QPlainTextEdit {
    background-color: #1b2029;
    alternate-background-color: #202631;
    color: #e2e8f0;
    border: 1px solid #2e3646;
    border-radius: 4px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #232936;
    color: #94a3b8;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #2e3646;
    border-bottom: 1px solid #2e3646;
    font-weight: 600;
    font-size: 11px;
}

QGroupBox {
    background-color: #1d222c;
    border: 1px solid #2e3646;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
    font-weight: bold;
    color: #93c5fd;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
}

QLabel {
    color: #cbd5e1;
    font-size: 12px;
}

QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background-color: #141820;
    color: #f8fafc;
    border: 1px solid #364154;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
}

QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #3b82f6;
}

QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton#secondaryBtn {
    background-color: #283040;
    border-color: #3e4a61;
    color: #e2e8f0;
}

QPushButton#secondaryBtn:hover {
    background-color: #333d52;
}

QStatusBar {
    background-color: #13161c;
    color: #94a3b8;
    border-top: 1px solid #283040;
    font-size: 11px;
}
"""


LIGHT_CAD_STYLESHEET = """
QMainWindow {
    background-color: #f1f5f9;
    color: #0f172a;
}

QMenuBar {
    background-color: #ffffff;
    color: #1e293b;
    border-bottom: 1px solid #cbd5e1;
    padding: 2px;
    font-size: 12px;
}

QMenuBar::item:selected {
    background-color: #e2e8f0;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #cbd5e1;
    spacing: 4px;
    padding: 4px 6px;
}

QToolButton {
    background-color: #f8fafc;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 4px 7px;
    font-weight: 600;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
    color: #1d4ed8;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #2563eb;
    border-color: #1d4ed8;
    color: #ffffff;
}

QDockWidget {
    color: #0f172a;
    font-weight: bold;
    font-size: 12px;
    titlebar-close-icon: url(none);
}

QDockWidget::title {
    background-color: #e2e8f0;
    border-top: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    padding: 7px 10px;
    text-align: left;
    color: #0f172a;
}

QTreeWidget, QTableWidget, QPlainTextEdit {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #334155;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    font-weight: 600;
    font-size: 11px;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
    font-weight: bold;
    color: #1d4ed8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
}

QLabel {
    color: #1e293b;
    font-size: 12px;
}

QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
}

QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #2563eb;
}

QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton#secondaryBtn {
    background-color: #f8fafc;
    border-color: #cbd5e1;
    color: #1e293b;
}

QPushButton#secondaryBtn:hover {
    background-color: #e2e8f0;
    border-color: #94a3b8;
}

QStatusBar {
    background-color: #e2e8f0;
    color: #334155;
    border-top: 1px solid #cbd5e1;
    font-size: 11px;
}
"""


def apply_theme(app: QApplication, mode: str = "dark") -> None:
    """Applies either the Dark ('dark') or White ('light') engineering theme to the Qt application."""
    global _CURRENT_THEME
    _CURRENT_THEME = "light" if mode == "light" else "dark"

    app.setStyle("Fusion")
    palette = QPalette()

    if _CURRENT_THEME == "light":
        palette.setColor(QPalette.ColorRole.Window, QColor("#f1f5f9"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8fafc"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#f8fafc"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)
        app.setStyleSheet(LIGHT_CAD_STYLESHEET)
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#161920"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e2e8f0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#141820"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e232d"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1e2430"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8fafc"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e2e8f0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#232936"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e8f0"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)
        app.setStyleSheet(DARK_CAD_STYLESHEET)


def apply_dark_cad_theme(app: QApplication) -> None:
    """Backwards-compatible alias for applying the Dark CAD theme."""
    apply_theme(app, "dark")
