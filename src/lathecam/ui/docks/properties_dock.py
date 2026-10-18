from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from lathecam.cam.finishing import CompensationMode
from lathecam.models.project import LatheProject, OperationNode, OperationType
from lathecam.models.stock import Stock


class PropertiesInspectorDock(QDockWidget):
    """Dynamic Property Inspector for editing Stock dimensions and CAM Operation parameters."""

    parameters_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Property Inspector", parent)
        self.setObjectName("PropertiesInspectorDock")
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)

        self._project: LatheProject | None = None
        self._active_op: OperationNode | None = None
        self._updating = False

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # 1. Stock Setup GroupBox
        self.stock_group = QGroupBox("Workpiece Stock Setup")
        stock_form = QFormLayout(self.stock_group)

        self.spin_stock_od = QDoubleSpinBox()
        self.spin_stock_od.setRange(2.0, 500.0)
        self.spin_stock_od.setSuffix(" mm")
        self.spin_stock_od.setDecimals(2)
        self.spin_stock_od.valueChanged.connect(self._on_stock_edited)

        self.spin_stock_z_start = QDoubleSpinBox()
        self.spin_stock_z_start.setRange(0.0, 50.0)
        self.spin_stock_z_start.setSuffix(" mm")
        self.spin_stock_z_start.setDecimals(2)
        self.spin_stock_z_start.valueChanged.connect(self._on_stock_edited)

        self.spin_stock_z_end = QDoubleSpinBox()
        self.spin_stock_z_end.setRange(-500.0, -2.0)
        self.spin_stock_z_end.setSuffix(" mm")
        self.spin_stock_z_end.setDecimals(2)
        self.spin_stock_z_end.valueChanged.connect(self._on_stock_edited)

        stock_form.addRow("Stock Outer Ø (OD):", self.spin_stock_od)
        stock_form.addRow("Face Allowance (Z+):", self.spin_stock_z_start)
        stock_form.addRow("Chuck Limit (Z-):", self.spin_stock_z_end)
        main_layout.addWidget(self.stock_group)

        # 2. Operation Parameters GroupBox
        self.op_group = QGroupBox("Selected CAM Operation")
        op_form = QFormLayout(self.op_group)

        self.lbl_op_title = QLabel("All Operations (Overview)")
        self.lbl_op_title.setStyleSheet("color: #60a5fa; font-weight: bold;")

        self.combo_tool = QComboBox()
        self.combo_tool.currentIndexChanged.connect(self._on_op_edited)

        self.spin_doc = QDoubleSpinBox()
        self.spin_doc.setRange(0.1, 20.0)
        self.spin_doc.setSingleStep(0.2)
        self.spin_doc.setSuffix(" mm")
        self.spin_doc.setDecimals(2)
        self.spin_doc.valueChanged.connect(self._on_op_edited)

        self.spin_allowance = QDoubleSpinBox()
        self.spin_allowance.setRange(0.0, 10.0)
        self.spin_allowance.setSingleStep(0.1)
        self.spin_allowance.setSuffix(" mm")
        self.spin_allowance.setDecimals(2)
        self.spin_allowance.valueChanged.connect(self._on_op_edited)

        self.spin_feed = QDoubleSpinBox()
        self.spin_feed.setRange(0.01, 5.0)
        self.spin_feed.setSingleStep(0.02)
        self.spin_feed.setSuffix(" mm/rev")
        self.spin_feed.setDecimals(3)
        self.spin_feed.valueChanged.connect(self._on_op_edited)

        self.spin_css = QDoubleSpinBox()
        self.spin_css.setRange(10.0, 1000.0)
        self.spin_css.setSingleStep(10.0)
        self.spin_css.setSuffix(" m/min")
        self.spin_css.setDecimals(0)
        self.spin_css.valueChanged.connect(self._on_op_edited)

        self.spin_max_rpm = QSpinBox()
        self.spin_max_rpm.setRange(100, 6000)
        self.spin_max_rpm.setSingleStep(100)
        self.spin_max_rpm.setSuffix(" RPM")
        self.spin_max_rpm.valueChanged.connect(self._on_op_edited)

        self.combo_comp = QComboBox()
        self.combo_comp.addItem("Computer TNRC (PyClipper)", CompensationMode.COMPUTER)
        self.combo_comp.addItem("Controller Comp (G41/G42)", CompensationMode.CONTROLLER)
        self.combo_comp.currentIndexChanged.connect(self._on_op_edited)

        self.spin_pitch = QDoubleSpinBox()
        self.spin_pitch.setRange(0.25, 6.0)
        self.spin_pitch.setSingleStep(0.25)
        self.spin_pitch.setSuffix(" mm")
        self.spin_pitch.setDecimals(2)
        self.spin_pitch.valueChanged.connect(self._on_op_edited)

        self.spin_peck = QDoubleSpinBox()
        self.spin_peck.setRange(0.2, 25.0)
        self.spin_peck.setSingleStep(0.5)
        self.spin_peck.setSuffix(" mm")
        self.spin_peck.setDecimals(2)
        self.spin_peck.valueChanged.connect(self._on_op_edited)

        op_form.addRow("Operation:", self.lbl_op_title)
        op_form.addRow("Turret Tool:", self.combo_tool)
        op_form.addRow("Depth of Cut (DOC):", self.spin_doc)
        op_form.addRow("Finish Allowance:", self.spin_allowance)
        op_form.addRow("Feed Rate (G95):", self.spin_feed)
        op_form.addRow("CSS Speed (G96 S):", self.spin_css)
        op_form.addRow("Max Spindle (G96 D):", self.spin_max_rpm)
        op_form.addRow("Nose Comp Mode:", self.combo_comp)
        op_form.addRow("Thread Pitch (P):", self.spin_pitch)
        op_form.addRow("Peck Depth (Q):", self.spin_peck)

        main_layout.addWidget(self.op_group)

        # 3. Simulation & Verification Metrics GroupBox
        self.sim_group = QGroupBox("2D Shapely Verification")
        sim_form = QFormLayout(self.sim_group)
        self.lbl_rest_area = QLabel("0.00 mm²")
        self.lbl_gouge_status = QLabel("✓ Collision-Free (0.00 mm²)")
        self.lbl_gouge_status.setStyleSheet("color: #22c55e; font-weight: bold;")
        sim_form.addRow("Uncut Rest Area:", self.lbl_rest_area)
        sim_form.addRow("Gouge Check:", self.lbl_gouge_status)
        main_layout.addWidget(self.sim_group)

        self.btn_recalc = QPushButton("⟳ Recalculate Toolpaths & G-Code")
        self.btn_recalc.clicked.connect(self.parameters_changed.emit)
        main_layout.addWidget(self.btn_recalc)

        main_layout.addStretch()
        self.setWidget(container)

    def set_project(self, project: LatheProject) -> None:
        self._project = project
        self._updating = True

        self.combo_tool.clear()
        for t_id, tool in sorted(project.tools.items()):
            self.combo_tool.addItem(f"T{t_id}: {tool.name} (R{tool.nose_radius_mm})", t_id)

        self.spin_stock_od.setValue(project.stock.od_mm)
        self.spin_stock_z_start.setValue(project.stock.z_start_mm)
        self.spin_stock_z_end.setValue(project.stock.z_end_mm)

        self.update_simulation_labels()
        self._updating = False

        if project.operations:
            self.inspect_operation(project.operations[1] if len(project.operations) > 1 else project.operations[0])

    def update_simulation_labels(self) -> None:
        if self._project is None or self._project.simulation_result is None:
            return
        sim = self._project.simulation_result
        self.lbl_rest_area.setText(f"{sim.rest_area_mm2:.2f} mm²")
        if sim.is_gouged:
            self.lbl_gouge_status.setText(f"⚠ GOUGE DETECTED ({sim.gouge_area_mm2:.3f} mm²)")
            self.lbl_gouge_status.setStyleSheet("color: #ef4444; font-weight: bold;")
        else:
            self.lbl_gouge_status.setText("✓ Collision-Free (0.000 mm²)")
            self.lbl_gouge_status.setStyleSheet("color: #22c55e; font-weight: bold;")

    def inspect_operation(self, op: OperationNode | None) -> None:
        self._active_op = op
        self._updating = True
        if op is None:
            self.lbl_op_title.setText("All Operations (Full Setup)")
            self.op_group.setEnabled(False)
            self._updating = False
            return

        self.op_group.setEnabled(True)
        self.lbl_op_title.setText(f"{op.name}")

        idx = self.combo_tool.findData(op.tool_id)
        if idx >= 0:
            self.combo_tool.setCurrentIndex(idx)

        self.spin_doc.setValue(op.doc_mm)
        self.spin_allowance.setValue(op.finish_allowance_mm)
        self.spin_feed.setValue(op.feed_mm_rev)
        self.spin_css.setValue(op.css_m_min)
        self.spin_max_rpm.setValue(op.max_rpm)

        comp_idx = self.combo_comp.findData(op.comp_mode)
        if comp_idx >= 0:
            self.combo_comp.setCurrentIndex(comp_idx)

        self.spin_pitch.setValue(op.pitch_mm)
        self.spin_peck.setValue(op.peck_depth_mm)

        # Enable relevant controls by operation type
        is_rough = op.op_type == OperationType.ROUGHING
        is_finish = op.op_type == OperationType.FINISHING
        is_thread = op.op_type == OperationType.THREADING
        is_peck = op.op_type in (OperationType.PARTING, OperationType.DRILLING)

        self.spin_doc.setEnabled(is_rough)
        self.spin_allowance.setEnabled(is_rough)
        self.combo_comp.setEnabled(is_finish)
        self.spin_pitch.setEnabled(is_thread)
        self.spin_peck.setEnabled(is_peck)

        self._updating = False

    def _on_stock_edited(self) -> None:
        if self._updating or self._project is None:
            return
        try:
            self._project.stock = Stock(
                od_mm=self.spin_stock_od.value(),
                z_start_mm=self.spin_stock_z_start.value(),
                z_end_mm=self.spin_stock_z_end.value(),
            )
            self.parameters_changed.emit()
        except ValueError:
            pass

    def _on_op_edited(self) -> None:
        if self._updating or self._active_op is None:
            return
        op = self._active_op
        tool_id = self.combo_tool.currentData()
        if tool_id is not None:
            op.tool_id = int(tool_id)
        op.doc_mm = self.spin_doc.value()
        op.finish_allowance_mm = self.spin_allowance.value()
        op.feed_mm_rev = self.spin_feed.value()
        op.css_m_min = self.spin_css.value()
        op.max_rpm = self.spin_max_rpm.value()
        comp_data = self.combo_comp.currentData()
        if comp_data is not None:
            op.comp_mode = comp_data
        op.pitch_mm = self.spin_pitch.value()
        op.peck_depth_mm = self.spin_peck.value()

        self.parameters_changed.emit()
