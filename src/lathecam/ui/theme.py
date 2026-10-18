from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


# CAD Viewport Color Palette
VIEWPORT_BG_TOP = "#141820"
VIEWPORT_BG_BOTTOM = "#222936"
STOCK_MESH_COLOR = "#38bdf8"      # Translucent sky blue stock cylinder
PART_MESH_COLOR = "#94a3b8"       # Machined steel metallic silver-slate
CUT_STOCK_COLOR = "#64748b"       # Simulated cut stock
SHADOW_POLY_COLOR = "#f59e0b"     # Amber undercut shadow overlay
GOUGE_POLY_COLOR = "#ef4444"      # Bright red gouge alert
REST_POLY_COLOR = "#3b82f6"       # Blue uncut rest material

# Toolpath Wireframe Colors
COLOR_RAPID_G0 = "#ef4444"        # Red dashed rapid moves
COLOR_CUT_G1 = "#22c55e"          # Bright green linear cuts
COLOR_ARC_G2_G3 = "#06b6d4"       # Cyan circular arc moves
COLOR_THREAD_G33 = "#eab308"      # Gold/yellow synchronized thread passes


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
    spacing: 6px;
    padding: 5px 8px;
}

QToolButton {
    background-color: #262d3b;
    color: #e2e8f0;
    border: 1px solid #364154;
    border-radius: 5px;
    padding: 5px 10px;
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


def apply_dark_cad_theme(app: QApplication) -> None:
    """Applies the SolidWorks/Fusion-inspired dark engineering theme to the Qt application."""
    app.setStyle("Fusion")
    palette = QPalette()
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
