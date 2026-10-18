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


class ToolTurretDock(QDockWidget):
    """Displays the LinuxCNC Tool Table & Turret Library (ISO Insert Geometry, Nose Radius, Orientation 1-9)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Tool Turret Library (LinuxCNC)", parent)
        self.setObjectName("ToolTurretDock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Pocket",
            "Description",
            "Shape",
            "Nose R",
            "Clearance / Lead",
            "Orient (Q)",
        ])
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

    def set_project(self, project: LatheProject) -> None:
        tools = sorted(project.tools.values(), key=lambda t: t.tool_id)
        self.table.setRowCount(len(tools))

        for row, tool in enumerate(tools):
            t_item = QTableWidgetItem(f"T{tool.tool_id}")
            t_item.setForeground(QBrush(QColor("#38bdf8")))
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
            q_item.setForeground(QBrush(QColor("#f59e0b")))
            self.table.setItem(row, 5, q_item)
