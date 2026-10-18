from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lathecam.models.project import LatheProject
from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_current_theme


class ToolTurretDock(QDockWidget):
    """Displays the Tool Table & Turret Library (ISO Insert Geometry, Nose Radius, Orientation 1-9)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("tools.dock_title"), parent)
        self.setObjectName("ToolTurretDock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        self._project: LatheProject | None = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(0, 6)
        self._update_headers()
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setWidget(container)

    def _update_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("tools.col_pocket"),
            tr("tools.col_desc"),
            tr("tools.col_shape"),
            tr("tools.col_nose_r"),
            tr("tools.col_angles"),
            tr("tools.col_orient"),
        ])

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("tools.dock_title"))
        self._update_headers()
        if self._project is not None:
            self.set_project(self._project)

    def set_project(self, project: LatheProject) -> None:
        self._project = project
        is_light = get_current_theme() == "light"
        tools = sorted(project.tools.values(), key=lambda t: t.tool_id)
        self.table.setRowCount(len(tools))

        for row, tool in enumerate(tools):
            t_item = QTableWidgetItem(f"T{tool.tool_id}")
            t_item.setForeground(QBrush(QColor("#0284c7" if is_light else "#38bdf8")))
            self.table.setItem(row, 0, t_item)

            self.table.setItem(row, 1, QTableWidgetItem(tool.name))
            self.table.setItem(row, 2, QTableWidgetItem(tool.insert_shape))
            self.table.setItem(row, 3, QTableWidgetItem(f"{tool.nose_radius_mm:.2f} mm"))
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(f"{tool.clearance_angle_deg:.0f}° / {tool.lead_angle_deg:.0f}°"),
            )
            q_item = QTableWidgetItem(f"Q{tool.orientation.value}")
            q_item.setForeground(QBrush(QColor("#d97706" if is_light else "#f59e0b")))
            self.table.setItem(row, 5, q_item)
