from __future__ import annotations

import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_current_theme


class GCodeSyntaxHighlighter(QSyntaxHighlighter):
    """Theme-aware syntax highlighter for LinuxCNC and Fanuc turning G-code."""

    def __init__(self, parent: QTextDocument) -> None:
        super().__init__(parent)
        self.rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []
        self.rebuild_rules()

    def rebuild_rules(self) -> None:
        is_light = get_current_theme() == "light"
        self.rules.clear()

        # G-words (G0, G1, G2, G3, G7, G18, G76, G83, G96, G97, etc.)
        fmt_g = QTextCharFormat()
        fmt_g.setForeground(QColor("#0284c7" if is_light else "#38bdf8"))
        fmt_g.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"\bG\d+(\.\d+)?\b"), fmt_g))

        # M-words & T-words
        fmt_m = QTextCharFormat()
        fmt_m.setForeground(QColor("#d97706" if is_light else "#f59e0b"))
        fmt_m.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"\b[MT]\d+\b"), fmt_m))

        # X and Z coordinates
        fmt_coord = QTextCharFormat()
        fmt_coord.setForeground(QColor("#15803d" if is_light else "#4ade80"))
        self.rules.append((re.compile(r"\b[XZ][-+]?\d*\.?\d+\b"), fmt_coord))

        # Arc offsets I, K and Thread/Drill params P, J, R, Q, H, E, L, D, S, F
        fmt_param = QTextCharFormat()
        fmt_param.setForeground(QColor("#7c3aed" if is_light else "#c084fc"))
        self.rules.append((re.compile(r"\b[IKPJRQHELDSF][-+]?\d*\.?\d+\b"), fmt_param))

        # Parenthetical comments (...)
        fmt_comment = QTextCharFormat()
        fmt_comment.setForeground(QColor("#64748b"))
        fmt_comment.setFontItalic(True)
        self.rules.append((re.compile(r"\([^)]*\)"), fmt_comment))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class GCodePreviewDock(QDockWidget):
    """Integrated G-code (.ngc / .nc) preview dock with dialect selector, syntax highlighting, and export."""

    export_requested = Signal()
    dialect_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("gcode.dock_title"), parent)
        self.setObjectName("GCodePreviewDock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        self._line_count: int = 0

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        self.combo_dialect = QComboBox()
        self.combo_dialect.addItem("LinuxCNC (.ngc)", "linuxcnc")
        self.combo_dialect.addItem("Fanuc 0i-TF (.nc)", "fanuc")
        self.combo_dialect.currentIndexChanged.connect(self._on_dialect_selected)
        header_row.addWidget(self.combo_dialect)

        self.lbl_stats = QLabel(tr("gcode.stats", count=0))
        self.lbl_stats.setStyleSheet("color: #64748b; font-size: 11px;")
        header_row.addWidget(self.lbl_stats)
        header_row.addStretch()

        self.btn_copy = QPushButton(tr("gcode.btn_copy"))
        self.btn_copy.setObjectName("secondaryBtn")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        header_row.addWidget(self.btn_copy)

        self.btn_export = QPushButton(tr("gcode.btn_export"))
        self.btn_export.clicked.connect(self.export_requested.emit)
        header_row.addWidget(self.btn_export)

        layout.addLayout(header_row)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)
        self.highlighter = GCodeSyntaxHighlighter(self.editor.document())

        layout.addWidget(self.editor)
        self.setWidget(container)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("gcode.dock_title"))
        self.btn_copy.setText(tr("gcode.btn_copy"))
        self.btn_export.setText(tr("gcode.btn_export"))
        self.lbl_stats.setText(tr("gcode.stats", count=self._line_count))
        self.highlighter.rebuild_rules()
        self.highlighter.rehighlight()

    def set_gcode(self, gcode_text: str) -> None:
        self.editor.setPlainText(gcode_text)
        self._line_count = len(gcode_text.splitlines())
        self.lbl_stats.setText(tr("gcode.stats", count=self._line_count))

    def _on_dialect_selected(self) -> None:
        dialect = self.combo_dialect.currentData()
        if dialect:
            self.dialect_changed.emit(str(dialect))

    def _copy_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.editor.toPlainText())
