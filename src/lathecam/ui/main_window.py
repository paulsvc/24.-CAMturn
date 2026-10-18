from __future__ import annotations

from pathlib import Path
import uuid
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from lathecam.cad.dxf_importer import DXFImporter
from lathecam.cad.step_importer import STEPImporter
from lathecam.models.project import LatheProject, OperationNode, OperationType
from lathecam.models.stock import Stock
from lathecam.ui.docks.gcode_dock import GCodePreviewDock
from lathecam.ui.docks.properties_dock import PropertiesInspectorDock
from lathecam.ui.docks.tools_dock import ToolTurretDock
from lathecam.ui.docks.tree_dock import FeatureTreeDock
from lathecam.ui.viewport.vtk_viewport import VTKLatheViewport


class LatheCAMMainWindow(QMainWindow):
    """Main SolidWorks/Fusion-inspired desktop CAD/CAM window for LatheCAM."""

    def __init__(self, project: LatheProject | None = None) -> None:
        super().__init__()
        self.setWindowTitle("LatheCAM — CNC Turning CAD/CAM Workbench (LinuxCNC G18 / G7)")
        self.resize(1540, 940)

        self.project: LatheProject = project or LatheProject.create_demo_project()
        self._active_op_id: str | None = None

        self._setup_toolbar()
        self._setup_central_viewport()
        self._setup_docks()
        self._setup_statusbar()

        self._sync_all_views()

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main CAM Ribbon", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        act_open = QAction("📂 Import STEP / DXF", self)
        act_open.triggered.connect(self.action_import_cad)
        toolbar.addAction(act_open)

        act_demo = QAction("⚙ Load Demo Shaft", self)
        act_demo.triggered.connect(self.action_load_demo)
        toolbar.addAction(act_demo)

        toolbar.addSeparator()

        act_all_ops = QAction("👁 View All Operations", self)
        act_all_ops.triggered.connect(self.action_view_all_operations)
        toolbar.addAction(act_all_ops)

        toolbar.addSeparator()

        act_add_face = QAction("➕ Face Op", self)
        act_add_face.triggered.connect(lambda: self.action_add_operation(OperationType.FACING))
        toolbar.addAction(act_add_face)

        act_add_rough = QAction("➕ OD Rough Op", self)
        act_add_rough.triggered.connect(lambda: self.action_add_operation(OperationType.ROUGHING))
        toolbar.addAction(act_add_rough)

        act_add_finish = QAction("➕ OD Finish Op", self)
        act_add_finish.triggered.connect(lambda: self.action_add_operation(OperationType.FINISHING))
        toolbar.addAction(act_add_finish)

        act_add_thread = QAction("➕ Thread G76", self)
        act_add_thread.triggered.connect(lambda: self.action_add_operation(OperationType.THREADING))
        toolbar.addAction(act_add_thread)

        act_add_drill = QAction("➕ Drill G83", self)
        act_add_drill.triggered.connect(lambda: self.action_add_operation(OperationType.DRILLING))
        toolbar.addAction(act_add_drill)

        act_add_part = QAction("➕ Peck Part-Off", self)
        act_add_part.triggered.connect(lambda: self.action_add_operation(OperationType.PARTING))
        toolbar.addAction(act_add_part)

        toolbar.addSeparator()

        act_export = QAction("💾 Post LinuxCNC (.ngc)", self)
        act_export.triggered.connect(self.action_export_gcode)
        toolbar.addAction(act_export)

    def _setup_central_viewport(self) -> None:
        self.viewport = VTKLatheViewport(self)
        self.setCentralWidget(self.viewport)

    def _setup_docks(self) -> None:
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )

        # Left Docks: Feature Tree (Top) + Tool Turret (Bottom)
        self.tree_dock = FeatureTreeDock(self)
        self.tree_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tree_dock)

        self.tools_dock = ToolTurretDock(self)
        self.tools_dock.setMinimumHeight(210)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)
        self.splitDockWidget(self.tree_dock, self.tools_dock, Qt.Orientation.Vertical)

        # Right Docks: Property Inspector (Top) + G-Code Output (Bottom)
        self.props_dock = PropertiesInspectorDock(self)
        self.props_dock.setMinimumWidth(370)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.props_dock)

        self.gcode_dock = GCodePreviewDock(self)
        self.gcode_dock.setMinimumHeight(300)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.gcode_dock)
        self.splitDockWidget(self.props_dock, self.gcode_dock, Qt.Orientation.Vertical)

        # Connect signals
        self.tree_dock.node_selected.connect(self._on_tree_node_selected)
        self.tree_dock.operations_changed.connect(self._on_project_modified)
        self.props_dock.parameters_changed.connect(self._on_project_modified)
        self.gcode_dock.export_requested.connect(self.action_export_gcode)

    def _setup_statusbar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        status.showMessage(
            "Ready • Kernel: Shapely 2.2 (GEOS) + PyClipper • Post: LinuxCNC G18 ZX Plane / G7 Diameter Mode"
        )

    def _sync_all_views(self) -> None:
        self.tree_dock.set_project(self.project)
        self.tools_dock.set_project(self.project)
        self.props_dock.set_project(self.project)
        self.gcode_dock.set_gcode(self.project.gcode_text)
        self.viewport.render_project(self.project, active_op_id=self._active_op_id)

    def _on_tree_node_selected(self, node_kind: str, node_id: str) -> None:
        if node_kind == "operation":
            self._active_op_id = node_id
            op = next((o for o in self.project.operations if o.op_id == node_id), None)
            self.props_dock.inspect_operation(op)
            if op is not None:
                self.statusBar().showMessage(
                    f"Inspecting {op.name} • Tool T{op.tool_id} • {len(op.commands)} MotionCmds"
                )
        else:
            self._active_op_id = None
            self.props_dock.inspect_operation(None)
            self.statusBar().showMessage(f"Showing all enabled operations for '{self.project.name}'")

        self.viewport.render_project(self.project, active_op_id=self._active_op_id)

    def _on_project_modified(self) -> None:
        self.project.recalculate_all()
        self.tree_dock.refresh()
        self.props_dock.update_simulation_labels()
        self.gcode_dock.set_gcode(self.project.gcode_text)
        self.viewport.render_project(self.project, active_op_id=self._active_op_id)

    def action_view_all_operations(self) -> None:
        self._active_op_id = None
        self.tree_dock.select_operation_by_id(None)
        self.props_dock.inspect_operation(None)
        self.viewport.render_project(self.project, active_op_id=None)

    def action_load_demo(self) -> None:
        self.project = LatheProject.create_demo_project()
        self._active_op_id = None
        self._sync_all_views()
        self.statusBar().showMessage("Loaded Stepped Threaded Drive Shaft Demo Project")

    def action_import_cad(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import 3D STEP or 2D DXF Turning Model",
            "",
            "CAD Files (*.step *.stp *.dxf);;STEP Files (*.step *.stp);;DXF Files (*.dxf)",
        )
        if not filepath:
            return
        self.load_cad_file(Path(filepath))

    def load_cad_file(self, path: Path) -> None:
        try:
            ext = path.suffix.lower()
            if ext in (".step", ".stp"):
                importer = STEPImporter()
                contour = importer.extract_contour(path)
            elif ext == ".dxf":
                importer = DXFImporter()
                contour = importer.load_contour(path)
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

            self.project.name = path.stem
            self.project.contour = contour
            # Automatically size stock with +4mm OD margin and +4mm length margin
            self.project.stock = Stock(
                od_mm=round(contour.x_max * 2.0 + 4.0, 1),
                z_start_mm=2.0,
                z_end_mm=round(contour.z_min - 4.0, 1),
            )
            self._on_project_modified()
            self._sync_all_views()
            self.statusBar().showMessage(f"Successfully imported {path.name} ({len(contour.points)} profile points)")
        except Exception as exc:
            QMessageBox.critical(self, "CAD Import Error", f"Failed to import {path.name}:\n{exc}")

    def action_add_operation(self, op_type: OperationType) -> None:
        idx = len(self.project.operations) + 1
        default_tool = {
            OperationType.FACING: 1,
            OperationType.ROUGHING: 1,
            OperationType.FINISHING: 2,
            OperationType.PARTING: 4,
            OperationType.THREADING: 5,
            OperationType.DRILLING: 6,
        }.get(op_type, 1)

        new_op = OperationNode(
            op_id=f"op_{uuid.uuid4().hex[:6]}",
            name=f"{idx}. {op_type.value}",
            op_type=op_type,
            tool_id=default_tool,
        )
        self.project.operations.append(new_op)
        self._active_op_id = new_op.op_id
        self._on_project_modified()
        self.tree_dock.select_operation_by_id(new_op.op_id)

    def action_export_gcode(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export LinuxCNC G-Code (.ngc)",
            f"{self.project.name.lower().replace(' ', '_')}.ngc",
            "LinuxCNC G-Code (*.ngc);;All Files (*)",
        )
        if not filepath:
            return
        Path(filepath).write_text(self.project.gcode_text, encoding="utf-8")
        self.statusBar().showMessage(f"Exported LinuxCNC G-Code to {filepath}")

    def capture_screenshot(self, output_path: str | Path) -> Path:
        """Captures a composite high-DPI screenshot of the entire Qt MainWindow + VTK OpenGL framebuffer."""
        out = Path(output_path)
        self.viewport.plotter.render()

        # Grab Qt widget hierarchy
        win_pixmap: QPixmap = self.grab()

        # Grab VTK OpenGL buffer directly as numpy RGB array and composite onto the interactor region
        try:
            vtk_rgb = self.viewport.plotter.screenshot(return_img=True)
            if vtk_rgb is not None and vtk_rgb.size > 0:
                h, w, ch = vtk_rgb.shape
                bytes_per_line = ch * w
                fmt = QImage.Format.Format_RGB888 if ch == 3 else QImage.Format.Format_RGBA8888
                vtk_qimg = QImage(vtk_rgb.data, w, h, bytes_per_line, fmt).copy()

                interactor_widget = self.viewport.plotter.interactor
                top_left: QPoint = interactor_widget.mapTo(self, QPoint(0, 0))
                target_w = interactor_widget.width()
                target_h = interactor_widget.height()

                painter = QPainter(win_pixmap)
                painter.drawImage(
                    top_left.x(),
                    top_left.y(),
                    vtk_qimg.scaled(
                        target_w,
                        target_h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
                painter.end()
        except Exception:
            pass

        win_pixmap.save(str(out), "PNG")
        return out
