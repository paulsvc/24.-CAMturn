from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lathecam.cam.tools import (
    ISO_INSERT_PRESETS,
    ISO_SHAPE_DESCRIPTIONS,
    LatheTool,
    ToolOrientation,
)
from lathecam.models.project import LatheProject
from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_current_theme


class Insert2DPreviewWidget(QWidget):
    """Interactive 2D blueprint preview rendering the exact ISO insert profile, nose radius, and IC circle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(280, 240)
        self._tool: LatheTool | None = None

    def set_tool(self, tool: LatheTool | None) -> None:
        self._tool = tool
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        is_light = get_current_theme() == "light"
        bg_color = QColor("#ffffff" if is_light else "#090d16")
        border_color = QColor("#cbd5e1" if is_light else "#1e293b")
        text_color = QColor("#0f172a" if is_light else "#e2e8f0")
        dim_color = QColor("#64748b" if is_light else "#94a3b8")

        # Frame background
        rect = QRectF(0, 0, self.width(), self.height())
        painter.fillRect(rect, bg_color)
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        if self._tool is None:
            painter.setPen(dim_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, tr("tools.no_tool_selected", default="No Tool Selected"))
            return

        tool = self._tool
        shape = (tool.insert_shape or "C").upper()
        ic = max(3.0, tool.inscribed_circle_mm)
        nose_r = max(0.0, tool.nose_radius_mm)
        thickness = max(0.5, tool.thickness_mm)
        tip_w = max(0.5, tool.tip_width_mm)

        # Compute bounding polygon in insert local space (mm)
        pts_mm: list[tuple[float, float]] = []

        if shape == "C":
            # 80° Rhombic Diamond
            l = ic / math.sin(math.radians(80.0))
            a1 = math.radians(10.0)
            a2 = math.radians(90.0)
            p1 = (l * math.cos(a1), l * math.sin(a1))
            p2 = (p1[0] + l * math.cos(a2), p1[1] + l * math.sin(a2))
            p3 = (l * math.cos(a2), l * math.sin(a2))
            pts_mm = [(0.0, 0.0), p1, p2, p3]

        elif shape == "D":
            # 55° Rhombic Diamond
            l = ic / math.sin(math.radians(55.0))
            a1 = math.radians(17.5)
            a2 = math.radians(72.5)
            p1 = (l * math.cos(a1), l * math.sin(a1))
            p2 = (p1[0] + l * math.cos(a2), p1[1] + l * math.sin(a2))
            p3 = (l * math.cos(a2), l * math.sin(a2))
            pts_mm = [(0.0, 0.0), p1, p2, p3]

        elif shape == "V":
            # 35° Rhombic Diamond
            l = ic / math.sin(math.radians(35.0))
            a1 = math.radians(27.5)
            a2 = math.radians(62.5)
            p1 = (l * math.cos(a1), l * math.sin(a1))
            p2 = (p1[0] + l * math.cos(a2), p1[1] + l * math.sin(a2))
            p3 = (l * math.cos(a2), l * math.sin(a2))
            pts_mm = [(0.0, 0.0), p1, p2, p3]

        elif shape == "W":
            # 80° Trigon (3 cutting corners)
            l = ic / math.sin(math.radians(80.0))
            pts_mm = [
                (0.0, 0.0),
                (l * 0.35, l * 0.95),
                (l * 1.0, l * 1.25),
                (l * 1.35, l * 0.70),
                (l * 0.80, 0.0),
            ]

        elif shape == "T":
            # 60° Equilateral Triangle
            l = ic * math.sqrt(3.0)
            a1 = math.radians(15.0)
            a2 = math.radians(75.0)
            pts_mm = [
                (0.0, 0.0),
                (l * math.cos(a1), l * math.sin(a1)),
                (l * math.cos(a2), l * math.sin(a2)),
            ]

        elif shape == "S":
            # 90° Square
            l = ic
            a1 = math.radians(5.0)
            a2 = math.radians(95.0)
            p1 = (l * math.cos(a1), l * math.sin(a1))
            p2 = (p1[0] + l * math.cos(a2), p1[1] + l * math.sin(a2))
            p3 = (l * math.cos(a2), l * math.sin(a2))
            pts_mm = [(0.0, 0.0), p1, p2, p3]

        elif shape == "R":
            # Round disk
            r = ic / 2.0
            n_pts = 48
            pts_mm = [
                (r + r * math.cos(math.radians(i * 360.0 / n_pts)),
                 r + r * math.sin(math.radians(i * 360.0 / n_pts)))
                for i in range(n_pts)
            ]

        elif shape == "K":
            # 55° Parallelogram
            l = ic / math.sin(math.radians(55.0))
            pts_mm = [
                (0.0, 0.0),
                (l * 0.4, l * 0.9),
                (l * 1.4, l * 0.9),
                (l * 1.0, 0.0),
            ]

        elif shape == "PART":
            # Parting blade rectangle
            pts_mm = [
                (0.0, 0.0),
                (0.0, 16.0),
                (tip_w, 16.0),
                (tip_w, 0.0),
            ]

        elif shape == "THREAD":
            # 60° Threading insert
            l = ic
            pts_mm = [
                (0.0, 0.0),
                (-l * 0.35, l * 0.6),
                (l * 0.85, l * 0.6),
                (l * 0.55, 0.0),
            ]

        elif shape == "DRILL":
            # Drill cone & flutes
            r = tip_w / 2.0
            cone_h = r / math.tan(math.radians(59.0))
            pts_mm = [
                (0.0, 0.0),
                (-r, cone_h),
                (-r, cone_h + 25.0),
                (r, cone_h + 25.0),
                (r, cone_h),
            ]

        else:
            # Fallback
            pts_mm = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

        # Calculate bounding box in mm
        xs = [p[0] for p in pts_mm]
        ys = [p[1] for p in pts_mm]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w_mm = max(1.0, max_x - min_x)
        h_mm = max(1.0, max_y - min_y)

        # Viewport layout and scaling
        margin = 38.0
        avail_w = self.width() - margin * 2.0
        avail_h = self.height() - margin * 2.0 - 24.0  # leave room for header/footer text
        scale = min(avail_w / w_mm, avail_h / h_mm)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0 + 8.0
        mid_mm_x = (min_x + max_x) / 2.0
        mid_mm_y = (min_y + max_y) / 2.0

        def to_screen(px: float, py: float) -> QPointF:
            sx = center_x + (px - mid_mm_x) * scale
            sy = center_y - (py - mid_mm_y) * scale  # Invert Y for screen coords
            return QPointF(sx, sy)

        # Draw Inscribed Circle (IC) as reference dashed circle
        if shape not in ("PART", "DRILL"):
            ic_center = to_screen(mid_mm_x, mid_mm_y)
            ic_r_px = (ic / 2.0) * scale
            painter.setPen(QPen(QColor("#0ea5e9" if is_light else "#38bdf8"), 1.2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(ic_center, ic_r_px, ic_r_px)

        # Draw Insert Body Polygon
        poly = QPolygonF([to_screen(px, py) for px, py in pts_mm])
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#fbbf24" if is_light else "#f59e0b"))
        grad.setColorAt(1.0, QColor("#d97706" if is_light else "#b45309"))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#78350f" if is_light else "#fef3c7"), 2.0))
        painter.drawPolygon(poly)

        # Draw Active Cutting Tip & Nose Radius Arc (Tip is at 0, 0)
        tip_pos = to_screen(0.0, 0.0)
        painter.setPen(QPen(QColor("#ef4444"), 2.5))
        painter.setBrush(QBrush(QColor("#dc2626")))
        painter.drawEllipse(tip_pos, 4.0, 4.0)

        # Crosshair lines at cutting tip
        painter.setPen(QPen(QColor("#ef4444"), 1.0, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(tip_pos.x() - 14, tip_pos.y()), QPointF(tip_pos.x() + 14, tip_pos.y()))
        painter.drawLine(QPointF(tip_pos.x(), tip_pos.y() - 14), QPointF(tip_pos.x(), tip_pos.y() + 14))

        # Annotations and dimension callouts
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(10, 20, f"ISO {shape} — {tool.name}")

        font_sm = QFont("Segoe UI", 8)
        painter.setFont(font_sm)
        painter.setPen(dim_color)

        if shape in ("PART", "DRILL"):
            painter.drawText(
                10,
                36,
                f"{tr('tools.preview_width')}: {tip_w:.2f} mm | {tr('tools.preview_thickness')}: {thickness:.2f} mm",
            )
        else:
            painter.drawText(
                10,
                36,
                f"{tr('tools.preview_ic')}: Ø{ic:.3f} mm | {tr('tools.preview_thickness')}: {thickness:.2f} mm | {tr('tools.preview_nose_r')}: {nose_r:.2f} mm",
            )

        painter.drawText(
            10,
            self.height() - 10,
            f"{tr('tools.preview_orient')}: Q{tool.orientation.value} | {tr('tools.preview_lead')}: {tool.lead_angle_deg:.1f}° | {tr('tools.preview_clearance')}: {tool.clearance_angle_deg:.1f}°",
        )
        painter.setPen(QColor("#ef4444"))
        painter.drawText(int(tip_pos.x() + 6), int(tip_pos.y() - 6), tr("tools.preview_tip"))


class ToolLibraryDialog(QDialog):
    """Full-featured ISO Insert & Lathe Tool Library Editor Dialog."""

    tools_updated = Signal()

    def __init__(
        self,
        project: LatheProject,
        parent: QWidget | None = None,
        initial_tool_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("tools.lib_title", default="Tool Turret & ISO Insert Library Editor"))
        self.resize(980, 680)

        self._project = project
        # Clone working tools so cancel won't alter project
        self._tools: dict[int, LatheTool] = {tid: t.clone() for tid, t in project.tools.items()}
        self._current_tool_id: int | None = initial_tool_id or (min(self._tools.keys()) if self._tools else None)

        self._init_ui()
        self._populate_table()
        if self._current_tool_id in self._tools:
            self._select_tool_in_table(self._current_tool_id)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ------------------ Left Panel: Tool Table ------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        lbl_turret = QLabel(tr("tools.turret_header", default="Tool Turret Pockets"))
        lbl_turret.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(lbl_turret)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            tr("tools.col_pocket", default="Pocket"),
            tr("tools.col_desc", default="Description"),
            tr("tools.col_shape", default="Shape"),
            tr("tools.col_nose_r", default="rε (mm)"),
            tr("tools.col_ic", default="IC (mm)"),
            tr("tools.col_orient", default="Orient"),
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        left_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton(tr("tools.btn_add_tool", default="➕ Add Tool"))
        self.btn_add.clicked.connect(self._action_add_tool)
        self.btn_duplicate = QPushButton(tr("tools.btn_duplicate", default="📋 Duplicate"))
        self.btn_duplicate.clicked.connect(self._action_duplicate_tool)
        self.btn_delete = QPushButton(tr("tools.btn_delete_tool", default="✕ Delete"))
        self.btn_delete.setObjectName("secondaryBtn")
        self.btn_delete.clicked.connect(self._action_delete_tool)
        self.btn_reset = QPushButton(tr("tools.btn_reset_defaults", default="↺ Defaults"))
        self.btn_reset.setObjectName("secondaryBtn")
        self.btn_reset.clicked.connect(self._action_reset_defaults)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_duplicate)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_reset)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left_widget)

        # ------------------ Right Panel: Insert Editor & Preview ------------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(10)

        # ISO Dimension Parameters Group
        self.grp_editor = QGroupBox(tr("tools.group_dimensions", default="ISO Insert Geometry & Dimensions"))
        form_layout = QFormLayout(self.grp_editor)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(6)

        # 1. Preset Selector
        self.combo_preset = QComboBox()
        self.combo_preset.addItem(tr("tools.preset_custom"), "")
        for preset_name in ISO_INSERT_PRESETS:
            self.combo_preset.addItem(f"★ {preset_name}", preset_name)
        self.combo_preset.currentIndexChanged.connect(self._on_preset_selected)
        form_layout.addRow(tr("tools.iso_preset", default="ISO Standard Preset:"), self.combo_preset)

        # 2. Tool ID & Description
        id_name_row = QHBoxLayout()
        self.spin_tool_id = QSpinBox()
        self.spin_tool_id.setRange(1, 99)
        self.spin_tool_id.valueChanged.connect(self._on_field_changed)
        id_name_row.addWidget(QLabel("T#"))
        id_name_row.addWidget(self.spin_tool_id)

        self.txt_name = QLineEdit()
        self.txt_name.textChanged.connect(self._on_field_changed)
        id_name_row.addWidget(self.txt_name, stretch=1)
        form_layout.addRow(tr("tools.pocket_name", default="Pocket & Name:"), id_name_row)

        # 3. Shape & Hand
        shape_hand_row = QHBoxLayout()
        self.combo_shape = QComboBox()
        for letter in ISO_SHAPE_DESCRIPTIONS:
            desc = tr(f"tools.shape_{letter.lower()}")
            self.combo_shape.addItem(f"{letter} — {desc}", letter)
        self.combo_shape.currentIndexChanged.connect(self._on_field_changed)
        shape_hand_row.addWidget(self.combo_shape, stretch=2)

        self.combo_hand = QComboBox()
        self.combo_hand.addItem(tr("tools.hand_r"), "R")
        self.combo_hand.addItem(tr("tools.hand_l"), "L")
        self.combo_hand.addItem(tr("tools.hand_n"), "N")
        self.combo_hand.currentIndexChanged.connect(self._on_field_changed)
        shape_hand_row.addWidget(self.combo_hand, stretch=1)
        form_layout.addRow(tr("tools.shape_hand", default="ISO Shape & Hand:"), shape_hand_row)

        # 4. Dimensional parameters in paired rows
        dim_row1 = QHBoxLayout()
        self.spin_ic = QDoubleSpinBox()
        self.spin_ic.setRange(1.0, 50.0)
        self.spin_ic.setDecimals(3)
        self.spin_ic.setSingleStep(0.5)
        self.spin_ic.setSuffix(" mm")
        self.spin_ic.valueChanged.connect(self._on_field_changed)
        dim_row1.addWidget(QLabel(tr("tools.param_ic")))
        dim_row1.addWidget(self.spin_ic)

        self.spin_thickness = QDoubleSpinBox()
        self.spin_thickness.setRange(0.5, 25.0)
        self.spin_thickness.setDecimals(2)
        self.spin_thickness.setSingleStep(0.2)
        self.spin_thickness.setSuffix(" mm")
        self.spin_thickness.valueChanged.connect(self._on_field_changed)
        dim_row1.addWidget(QLabel(tr("tools.param_thickness")))
        dim_row1.addWidget(self.spin_thickness)

        self.spin_nose_r = QDoubleSpinBox()
        self.spin_nose_r.setRange(0.0, 15.0)
        self.spin_nose_r.setDecimals(2)
        self.spin_nose_r.setSingleStep(0.1)
        self.spin_nose_r.setSuffix(" mm")
        self.spin_nose_r.valueChanged.connect(self._on_field_changed)
        dim_row1.addWidget(QLabel(tr("tools.param_nose_r")))
        dim_row1.addWidget(self.spin_nose_r)
        form_layout.addRow(tr("tools.dimensions", default="Dimensions:"), dim_row1)

        dim_row2 = QHBoxLayout()
        self.spin_edge_len = QDoubleSpinBox()
        self.spin_edge_len.setRange(1.0, 100.0)
        self.spin_edge_len.setDecimals(1)
        self.spin_edge_len.setSuffix(" mm")
        self.spin_edge_len.valueChanged.connect(self._on_field_changed)
        dim_row2.addWidget(QLabel(tr("tools.param_edge_len")))
        dim_row2.addWidget(self.spin_edge_len)

        self.spin_tip_width = QDoubleSpinBox()
        self.spin_tip_width.setRange(0.5, 50.0)
        self.spin_tip_width.setDecimals(2)
        self.spin_tip_width.setSuffix(" mm")
        self.spin_tip_width.valueChanged.connect(self._on_field_changed)
        dim_row2.addWidget(QLabel(tr("tools.param_tip_width")))
        dim_row2.addWidget(self.spin_tip_width)

        self.spin_max_doc = QDoubleSpinBox()
        self.spin_max_doc.setRange(0.1, 50.0)
        self.spin_max_doc.setDecimals(2)
        self.spin_max_doc.setSuffix(" mm")
        self.spin_max_doc.valueChanged.connect(self._on_field_changed)
        dim_row2.addWidget(QLabel(tr("tools.param_max_doc")))
        dim_row2.addWidget(self.spin_max_doc)
        form_layout.addRow(tr("tools.cut_limits", default="Cutting Limits:"), dim_row2)

        # 5. Angles and Orientation
        angles_row = QHBoxLayout()
        self.spin_lead_angle = QDoubleSpinBox()
        self.spin_lead_angle.setRange(0.0, 180.0)
        self.spin_lead_angle.setDecimals(1)
        self.spin_lead_angle.setSuffix("°")
        self.spin_lead_angle.valueChanged.connect(self._on_field_changed)
        angles_row.addWidget(QLabel(tr("tools.param_lead_angle")))
        angles_row.addWidget(self.spin_lead_angle)

        self.spin_clearance_angle = QDoubleSpinBox()
        self.spin_clearance_angle.setRange(0.0, 90.0)
        self.spin_clearance_angle.setDecimals(1)
        self.spin_clearance_angle.setSuffix("°")
        self.spin_clearance_angle.valueChanged.connect(self._on_field_changed)
        angles_row.addWidget(QLabel(tr("tools.param_clearance")))
        angles_row.addWidget(self.spin_clearance_angle)

        self.combo_orientation = QComboBox()
        for q in range(1, 10):
            self.combo_orientation.addItem(tr(f"tools.orient_q{q}"), q)
        self.combo_orientation.currentIndexChanged.connect(self._on_field_changed)
        angles_row.addWidget(QLabel(tr("tools.param_orient")))
        angles_row.addWidget(self.combo_orientation)
        form_layout.addRow(tr("tools.angles_orient", default="Angles & Orient:"), angles_row)

        right_layout.addWidget(self.grp_editor)

        # Live 2D Insert Silhouette Preview
        self.preview_widget = Insert2DPreviewWidget()
        right_layout.addWidget(self.preview_widget, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

        # ------------------ Bottom Action Bar ------------------
        bottom_row = QHBoxLayout()
        self.btn_import = QPushButton(tr("tools.import_lib", default="📁 Import Library (.json)"))
        self.btn_import.setObjectName("secondaryBtn")
        self.btn_import.clicked.connect(self._action_import_library)
        bottom_row.addWidget(self.btn_import)

        self.btn_export = QPushButton(tr("tools.export_lib", default="💾 Export Library (.json)"))
        self.btn_export.setObjectName("secondaryBtn")
        self.btn_export.clicked.connect(self._action_export_library)
        bottom_row.addWidget(self.btn_export)

        bottom_row.addStretch()

        self.btn_cancel = QPushButton(tr("common.cancel", default="Cancel"))
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton(tr("common.apply_and_close", default="Apply to Project"))
        self.btn_ok.clicked.connect(self._action_apply)
        bottom_row.addWidget(self.btn_ok)

        main_layout.addLayout(bottom_row)

    def _populate_table(self) -> None:
        self.table.blockSignals(True)
        sorted_tools = sorted(self._tools.values(), key=lambda t: t.tool_id)
        self.table.setRowCount(len(sorted_tools))
        is_light = get_current_theme() == "light"

        for row, tool in enumerate(sorted_tools):
            p_item = QTableWidgetItem(f"T{tool.tool_id}")
            p_item.setForeground(QBrush(QColor("#0284c7" if is_light else "#38bdf8")))
            p_item.setData(Qt.ItemDataRole.UserRole, tool.tool_id)
            self.table.setItem(row, 0, p_item)

            self.table.setItem(row, 1, QTableWidgetItem(tool.name))
            self.table.setItem(row, 2, QTableWidgetItem(tool.insert_shape))
            self.table.setItem(row, 3, QTableWidgetItem(f"{tool.nose_radius_mm:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{tool.inscribed_circle_mm:.2f}"))

            q_item = QTableWidgetItem(f"Q{tool.orientation.value}")
            q_item.setForeground(QBrush(QColor("#d97706" if is_light else "#f59e0b")))
            self.table.setItem(row, 5, q_item)

        self.table.blockSignals(False)

    def _select_tool_in_table(self, tool_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == tool_id:
                self.table.selectRow(row)
                break

    def _on_table_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        tool_id = item.data(Qt.ItemDataRole.UserRole)
        if tool_id in self._tools:
            self._current_tool_id = tool_id
            self._load_tool_into_editor(self._tools[tool_id])

    def _load_tool_into_editor(self, tool: LatheTool) -> None:
        self.grp_editor.blockSignals(True)
        for w_type in (QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox):
            for child in self.grp_editor.findChildren(w_type):
                child.blockSignals(True)

        self.spin_tool_id.setValue(tool.tool_id)
        self.txt_name.setText(tool.name)

        idx_shape = self.combo_shape.findData(tool.insert_shape)
        if idx_shape >= 0:
            self.combo_shape.setCurrentIndex(idx_shape)

        idx_hand = self.combo_hand.findData(tool.hand)
        if idx_hand >= 0:
            self.combo_hand.setCurrentIndex(idx_hand)

        self.spin_ic.setValue(tool.inscribed_circle_mm)
        self.spin_thickness.setValue(tool.thickness_mm)
        self.spin_nose_r.setValue(tool.nose_radius_mm)
        self.spin_edge_len.setValue(tool.cutting_edge_length_mm)
        self.spin_tip_width.setValue(tool.tip_width_mm)
        self.spin_max_doc.setValue(tool.max_doc_mm)
        self.spin_lead_angle.setValue(tool.lead_angle_deg)
        self.spin_clearance_angle.setValue(tool.clearance_angle_deg)

        idx_orient = self.combo_orientation.findData(tool.orientation.value)
        if idx_orient >= 0:
            self.combo_orientation.setCurrentIndex(idx_orient)

        # Match preset combo if applicable
        self.combo_preset.blockSignals(True)
        preset_idx = 0
        for i in range(1, self.combo_preset.count()):
            p_key = self.combo_preset.itemData(i)
            p_data = ISO_INSERT_PRESETS.get(p_key, {})
            if (
                p_data.get("insert_shape") == tool.insert_shape
                and abs(p_data.get("inscribed_circle_mm", 0) - tool.inscribed_circle_mm) < 0.1
                and abs(p_data.get("nose_radius_mm", 0) - tool.nose_radius_mm) < 0.05
            ):
                preset_idx = i
                break
        self.combo_preset.setCurrentIndex(preset_idx)
        self.combo_preset.blockSignals(False)

        for w_type in (QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox):
            for child in self.grp_editor.findChildren(w_type):
                child.blockSignals(False)
        self.grp_editor.blockSignals(False)

        self.preview_widget.set_tool(tool)

    def _on_preset_selected(self, index: int) -> None:
        if index <= 0 or self._current_tool_id not in self._tools:
            return
        preset_key = self.combo_preset.itemData(index)
        tool = self._tools[self._current_tool_id]
        if tool.apply_preset(preset_key):
            self._load_tool_into_editor(tool)
            self._update_table_row_for_tool(tool)

    def _on_field_changed(self) -> None:
        if self._current_tool_id not in self._tools:
            return
        tool = self._tools[self._current_tool_id]

        new_tool_id = self.spin_tool_id.value()
        if new_tool_id != self._current_tool_id:
            # Check collision
            if new_tool_id in self._tools and new_tool_id != self._current_tool_id:
                QMessageBox.warning(
                    self,
                    tr("tools.msg_pocket_collision_title"),
                    tr("tools.msg_pocket_collision", tool_id=new_tool_id),
                )
                self.spin_tool_id.blockSignals(True)
                self.spin_tool_id.setValue(self._current_tool_id)
                self.spin_tool_id.blockSignals(False)
                return
            del self._tools[self._current_tool_id]
            self._tools[new_tool_id] = tool
            self._current_tool_id = new_tool_id
            tool.tool_id = new_tool_id

        tool.name = self.txt_name.text()
        tool.insert_shape = str(self.combo_shape.currentData())
        tool.hand = str(self.combo_hand.currentData())
        tool.inscribed_circle_mm = self.spin_ic.value()
        tool.thickness_mm = self.spin_thickness.value()
        tool.nose_radius_mm = self.spin_nose_r.value()
        tool.cutting_edge_length_mm = self.spin_edge_len.value()
        tool.tip_width_mm = self.spin_tip_width.value()
        tool.max_doc_mm = self.spin_max_doc.value()
        tool.lead_angle_deg = self.spin_lead_angle.value()
        tool.clearance_angle_deg = self.spin_clearance_angle.value()
        tool.orientation = ToolOrientation(int(self.combo_orientation.currentData()))

        self._update_table_row_for_tool(tool)
        self.preview_widget.set_tool(tool)

    def _update_table_row_for_tool(self, tool: LatheTool) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == tool.tool_id:
                self.table.item(row, 1).setText(tool.name)
                self.table.item(row, 2).setText(tool.insert_shape)
                self.table.item(row, 3).setText(f"{tool.nose_radius_mm:.2f}")
                self.table.item(row, 4).setText(f"{tool.inscribed_circle_mm:.2f}")
                self.table.item(row, 5).setText(f"Q{tool.orientation.value}")
                break

    def _action_add_tool(self) -> None:
        next_id = 1
        while next_id in self._tools:
            next_id += 1
        new_tool = LatheTool.cnmg_roughing(tool_id=next_id)
        new_tool.name = f"T{next_id} ISO Turning Tool"
        self._tools[next_id] = new_tool
        self._populate_table()
        self._select_tool_in_table(next_id)

    def _action_duplicate_tool(self) -> None:
        if self._current_tool_id not in self._tools:
            return
        next_id = 1
        while next_id in self._tools:
            next_id += 1
        cloned = self._tools[self._current_tool_id].clone(new_tool_id=next_id)
        self._tools[next_id] = cloned
        self._populate_table()
        self._select_tool_in_table(next_id)

    def _action_delete_tool(self) -> None:
        if len(self._tools) <= 1:
            QMessageBox.information(
                self,
                tr("tools.msg_delete_min_title"),
                tr("tools.msg_delete_min"),
            )
            return
        if self._current_tool_id not in self._tools:
            return
        del self._tools[self._current_tool_id]
        self._current_tool_id = min(self._tools.keys())
        self._populate_table()
        self._select_tool_in_table(self._current_tool_id)

    def _action_reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            tr("tools.msg_reset_title"),
            tr("tools.msg_reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tools = LatheProject.default_tool_turret()
            self._current_tool_id = min(self._tools.keys())
            self._populate_table()
            self._select_tool_in_table(self._current_tool_id)

    def _action_export_library(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            tr("tools.msg_export_title"),
            "lathecam_tool_library.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not filepath:
            return
        data = {
            "version": "1.0",
            "tools": [t.to_dict() for t in sorted(self._tools.values(), key=lambda t: t.tool_id)],
        }
        Path(filepath).write_text(json.dumps(data, indent=2), encoding="utf-8")
        QMessageBox.information(
            self,
            tr("tools.msg_export_success_title"),
            tr("tools.msg_export_success", count=len(self._tools), name=Path(filepath).name),
        )

    def _action_import_library(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            tr("tools.msg_import_title"),
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not filepath:
            return
        try:
            data = json.loads(Path(filepath).read_text(encoding="utf-8"))
            loaded_tools: dict[int, LatheTool] = {}
            for td in data.get("tools", []):
                t = LatheTool.from_dict(td)
                loaded_tools[t.tool_id] = t
            if loaded_tools:
                self._tools = loaded_tools
                self._current_tool_id = min(self._tools.keys())
                self._populate_table()
                self._select_tool_in_table(self._current_tool_id)
                QMessageBox.information(
                    self,
                    tr("tools.msg_import_success_title"),
                    tr("tools.msg_import_success", count=len(loaded_tools), name=Path(filepath).name),
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("tools.msg_import_error_title"),
                tr("tools.msg_import_error", err=str(exc)),
            )

    def _action_apply(self) -> None:
        """Applies working tools back to the active LatheProject."""
        self._project.tools = {tid: t.clone() for tid, t in self._tools.items()}
        self._project.recalculate_all()
        self.tools_updated.emit()
        self.accept()
