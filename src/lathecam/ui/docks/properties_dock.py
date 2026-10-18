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
from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_current_theme


class PropertiesInspectorDock(QDockWidget):
    """Dynamic Property Inspector for editing Stock dimensions and CAM Operation parameters."""

    parameters_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("props.dock_title"), parent)
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
        self.stock_group = QGroupBox(tr("props.stock_group"))
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

        self.lbl_stock_od = QLabel(tr("props.stock_od"))
        self.lbl_stock_z_start = QLabel(tr("props.stock_z_start"))
        self.lbl_stock_z_end = QLabel(tr("props.stock_z_end"))

        stock_form.addRow(self.lbl_stock_od, self.spin_stock_od)
        stock_form.addRow(self.lbl_stock_z_start, self.spin_stock_z_start)
        stock_form.addRow(self.lbl_stock_z_end, self.spin_stock_z_end)
        main_layout.addWidget(self.stock_group)

        # 2. Operation Parameters GroupBox
        self.op_group = QGroupBox(tr("props.op_group"))
        op_form = QFormLayout(self.op_group)

        self.lbl_op_title = QLabel(tr("props.all_ops_overview"))
        self.lbl_op_title.setStyleSheet("color: #2563eb; font-weight: bold;")

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
        self.combo_comp.addItem(tr("props.comp_computer"), CompensationMode.COMPUTER)
        self.combo_comp.addItem(tr("props.comp_controller"), CompensationMode.CONTROLLER)
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

        self.lbl_op_row = QLabel(tr("props.lbl_op"))
        self.lbl_tool_row = QLabel(tr("props.lbl_tool"))
        self.lbl_doc_row = QLabel(tr("props.lbl_doc"))
        self.lbl_allowance_row = QLabel(tr("props.lbl_allowance"))
        self.lbl_feed_row = QLabel(tr("props.lbl_feed"))
        self.lbl_css_row = QLabel(tr("props.lbl_css"))
        self.lbl_max_rpm_row = QLabel(tr("props.lbl_max_rpm"))
        self.lbl_comp_row = QLabel(tr("props.lbl_comp"))
        self.lbl_pitch_row = QLabel(tr("props.lbl_pitch"))
        self.lbl_peck_row = QLabel(tr("props.lbl_peck"))

        op_form.addRow(self.lbl_op_row, self.lbl_op_title)
        op_form.addRow(self.lbl_tool_row, self.combo_tool)
        op_form.addRow(self.lbl_doc_row, self.spin_doc)
        op_form.addRow(self.lbl_allowance_row, self.spin_allowance)
        op_form.addRow(self.lbl_feed_row, self.spin_feed)
        op_form.addRow(self.lbl_css_row, self.spin_css)
        op_form.addRow(self.lbl_max_rpm_row, self.spin_max_rpm)
        op_form.addRow(self.lbl_comp_row, self.combo_comp)
        op_form.addRow(self.lbl_pitch_row, self.spin_pitch)
        op_form.addRow(self.lbl_peck_row, self.spin_peck)

        main_layout.addWidget(self.op_group)

        # 3. Simulation & Verification Metrics GroupBox
        self.sim_group = QGroupBox(tr("props.sim_group"))
        sim_form = QFormLayout(self.sim_group)
        self.lbl_rest_area_row = QLabel(tr("props.lbl_rest_area"))
        self.lbl_gouge_check_row = QLabel(tr("props.lbl_gouge_check"))
        self.lbl_rest_area = QLabel("0.00 mm²")
        self.lbl_gouge_status = QLabel(tr("props.collision_free"))
        self.lbl_gouge_status.setStyleSheet("color: #16a34a; font-weight: bold;")
        sim_form.addRow(self.lbl_rest_area_row, self.lbl_rest_area)
        sim_form.addRow(self.lbl_gouge_check_row, self.lbl_gouge_status)
        main_layout.addWidget(self.sim_group)

        self.btn_recalc = QPushButton(tr("props.btn_recalc"))
        self.btn_recalc.clicked.connect(self.parameters_changed.emit)
        main_layout.addWidget(self.btn_recalc)

        main_layout.addStretch()
        self.setWidget(container)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("props.dock_title"))
        self.stock_group.setTitle(tr("props.stock_group"))
        self.lbl_stock_od.setText(tr("props.stock_od"))
        self.lbl_stock_z_start.setText(tr("props.stock_z_start"))
        self.lbl_stock_z_end.setText(tr("props.stock_z_end"))

        self.op_group.setTitle(tr("props.op_group"))
        self.lbl_op_row.setText(tr("props.lbl_op"))
        self.lbl_tool_row.setText(tr("props.lbl_tool"))
        self.lbl_doc_row.setText(tr("props.lbl_doc"))
        self.lbl_allowance_row.setText(tr("props.lbl_allowance"))
        self.lbl_feed_row.setText(tr("props.lbl_feed"))
        self.lbl_css_row.setText(tr("props.lbl_css"))
        self.lbl_max_rpm_row.setText(tr("props.lbl_max_rpm"))
        self.lbl_comp_row.setText(tr("props.lbl_comp"))
        self.lbl_pitch_row.setText(tr("props.lbl_pitch"))
        self.lbl_peck_row.setText(tr("props.lbl_peck"))

        self._updating = True
        self.combo_comp.setItemText(0, tr("props.comp_computer"))
        self.combo_comp.setItemText(1, tr("props.comp_controller"))
        self._updating = False

        self.sim_group.setTitle(tr("props.sim_group"))
        self.lbl_rest_area_row.setText(tr("props.lbl_rest_area"))
        self.lbl_gouge_check_row.setText(tr("props.lbl_gouge_check"))
        self.btn_recalc.setText(tr("props.btn_recalc"))

        is_light = get_current_theme() == "light"
        self.lbl_op_title.setStyleSheet(
            f"color: {'#1d4ed8' if is_light else '#60a5fa'}; font-weight: bold;"
        )
        if self._active_op is None:
            self.lbl_op_title.setText(tr("props.all_ops_overview"))
        self.update_simulation_labels()

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
        is_light = get_current_theme() == "light"
        self.lbl_rest_area.setText(f"{sim.rest_area_mm2:.2f} mm²")
        if sim.is_gouged:
            self.lbl_gouge_status.setText(tr("props.gouge_detected", area=sim.gouge_area_mm2))
            self.lbl_gouge_status.setStyleSheet(
                f"color: {'#dc2626' if is_light else '#ef4444'}; font-weight: bold;"
            )
        else:
            self.lbl_gouge_status.setText(tr("props.collision_free"))
            self.lbl_gouge_status.setStyleSheet(
                f"color: {'#15803d' if is_light else '#22c55e'}; font-weight: bold;"
            )

    def inspect_operation(self, op: OperationNode | None) -> None:
        self._active_op = op
        self._updating = True
        if op is None:
            self.lbl_op_title.setText(tr("props.all_ops_overview"))
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
