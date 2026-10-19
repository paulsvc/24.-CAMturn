from __future__ import annotations

from pathlib import Path
import uuid
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
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
from lathecam.ui.i18n import get_language, set_language, tr
from lathecam.ui.theme import apply_theme, get_current_theme
from lathecam.ui.viewport.vtk_viewport import VTKLatheViewport


class LatheCAMMainWindow(QMainWindow):
    """Main SolidWorks/Fusion-inspired desktop CAD/CAM window for LatheCAM."""

    def __init__(self, project: LatheProject | None = None) -> None:
        super().__init__()
        self.setWindowTitle(tr("window.title"))
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

        self.act_open = QAction(tr("toolbar.import_cad"), self)
        self.act_open.triggered.connect(self.action_import_cad)
        toolbar.addAction(self.act_open)

        self.act_open_proj = QAction(tr("toolbar.open_lcam"), self)
        self.act_open_proj.triggered.connect(self.action_open_project)
        toolbar.addAction(self.act_open_proj)

        self.act_save_proj = QAction(tr("toolbar.save_lcam"), self)
        self.act_save_proj.triggered.connect(self.action_save_project)
        toolbar.addAction(self.act_save_proj)

        self.act_demo = QAction(tr("toolbar.load_demo"), self)
        self.act_demo.triggered.connect(self.action_load_demo)
        toolbar.addAction(self.act_demo)

        toolbar.addSeparator()

        self.act_all_ops = QAction(tr("toolbar.view_all"), self)
        self.act_all_ops.triggered.connect(self.action_view_all_operations)
        toolbar.addAction(self.act_all_ops)

        toolbar.addSeparator()

        self.act_add_face = QAction(tr("toolbar.add_face"), self)
        self.act_add_face.triggered.connect(lambda: self.action_add_operation(OperationType.FACING))
        toolbar.addAction(self.act_add_face)

        self.act_add_rough = QAction(tr("toolbar.add_rough"), self)
        self.act_add_rough.triggered.connect(lambda: self.action_add_operation(OperationType.ROUGHING))
        toolbar.addAction(self.act_add_rough)

        self.act_add_finish = QAction(tr("toolbar.add_finish"), self)
        self.act_add_finish.triggered.connect(lambda: self.action_add_operation(OperationType.FINISHING))
        toolbar.addAction(self.act_add_finish)

        self.act_add_thread = QAction(tr("toolbar.add_thread"), self)
        self.act_add_thread.triggered.connect(lambda: self.action_add_operation(OperationType.THREADING))
        toolbar.addAction(self.act_add_thread)

        self.act_add_drill = QAction(tr("toolbar.add_drill"), self)
        self.act_add_drill.triggered.connect(lambda: self.action_add_operation(OperationType.DRILLING))
        toolbar.addAction(self.act_add_drill)

        self.act_add_part = QAction(tr("toolbar.add_part"), self)
        self.act_add_part.triggered.connect(lambda: self.action_add_operation(OperationType.PARTING))
        toolbar.addAction(self.act_add_part)

        toolbar.addSeparator()

        self.act_export = QAction(tr("toolbar.post_gcode"), self)
        self.act_export.triggered.connect(self.action_export_gcode)
        toolbar.addAction(self.act_export)

        toolbar.addSeparator()

        # Theme Toggle Action (Dark <-> White)
        self.act_theme = QAction(
            tr("toolbar.theme_light") if get_current_theme() == "dark" else tr("toolbar.theme_dark"),
            self,
        )
        self.act_theme.triggered.connect(self.action_toggle_theme)
        toolbar.addAction(self.act_theme)

        # Language Selector Combo (English / Français)
        self.lbl_lang = QLabel(f" {tr('toolbar.lang_label')} ")
        toolbar.addWidget(self.lbl_lang)
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English (EN)", "en")
        self.combo_lang.addItem("Français (FR)", "fr")
        idx = self.combo_lang.findData(get_language())
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        toolbar.addWidget(self.combo_lang)

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
        self.tree_dock.assign_op_to_face_requested.connect(self.action_assign_operation_to_face)
        self.props_dock.parameters_changed.connect(self._on_project_modified)
        self.gcode_dock.export_requested.connect(self.action_export_gcode)
        self.gcode_dock.dialect_changed.connect(self._on_dialect_changed)
        self.viewport.face_selected.connect(self._on_viewport_face_selected)
        self.viewport.assign_op_to_face_requested.connect(self.action_assign_operation_to_face)

    def _setup_statusbar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        status.showMessage(tr("status.ready"))

    def _sync_all_views(self) -> None:
        self.tree_dock.set_project(self.project)
        self.tools_dock.set_project(self.project)
        self.props_dock.set_project(self.project)
        self.gcode_dock.set_gcode(self.project.gcode_text)
        self.viewport.render_project(self.project, active_op_id=self._active_op_id)

    def set_theme_mode(self, mode: str) -> None:
        """Applies 'dark' or 'light' (White) theme across the entire application and VTK viewport."""
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, mode)
        self.act_theme.setText(
            tr("toolbar.theme_light") if get_current_theme() == "dark" else tr("toolbar.theme_dark")
        )
        self.viewport.apply_theme_colors()
        self.tree_dock.retranslate_ui()
        self.tools_dock.retranslate_ui()
        self.props_dock.retranslate_ui()
        self.gcode_dock.retranslate_ui()
        self.statusBar().showMessage(tr("status.theme_changed", theme=get_current_theme().upper()))

    def action_toggle_theme(self) -> None:
        next_theme = "light" if get_current_theme() == "dark" else "dark"
        self.set_theme_mode(next_theme)

    def set_ui_language(self, lang: str) -> None:
        """Switches UI language ('en' or 'fr') and live-updates all docks, buttons, and labels."""
        set_language(lang)
        idx = self.combo_lang.findData(lang)
        if idx >= 0 and self.combo_lang.currentIndex() != idx:
            self.combo_lang.blockSignals(True)
            self.combo_lang.setCurrentIndex(idx)
            self.combo_lang.blockSignals(False)
        self.retranslate_ui()

    def _on_language_changed(self) -> None:
        lang = self.combo_lang.currentData()
        if lang:
            self.set_ui_language(str(lang))

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("window.title"))
        self.act_open.setText(tr("toolbar.import_cad"))
        self.act_open_proj.setText(tr("toolbar.open_lcam"))
        self.act_save_proj.setText(tr("toolbar.save_lcam"))
        self.act_demo.setText(tr("toolbar.load_demo"))
        self.act_all_ops.setText(tr("toolbar.view_all"))
        self.act_add_face.setText(tr("toolbar.add_face"))
        self.act_add_rough.setText(tr("toolbar.add_rough"))
        self.act_add_finish.setText(tr("toolbar.add_finish"))
        self.act_add_thread.setText(tr("toolbar.add_thread"))
        self.act_add_drill.setText(tr("toolbar.add_drill"))
        self.act_add_part.setText(tr("toolbar.add_part"))
        self.act_export.setText(tr("toolbar.post_gcode"))
        self.act_theme.setText(
            tr("toolbar.theme_light") if get_current_theme() == "dark" else tr("toolbar.theme_dark")
        )

        self.tree_dock.retranslate_ui()
        self.tools_dock.retranslate_ui()
        self.props_dock.retranslate_ui()
        self.gcode_dock.retranslate_ui()
        self.viewport.retranslate_ui()
        self.statusBar().showMessage(tr("status.lang_changed"))

    def _on_dialect_changed(self, dialect: str) -> None:
        self.project.post_dialect = dialect
        self.project.recalculate_all()
        self.tree_dock.refresh()
        self.gcode_dock.set_gcode(self.project.gcode_text)
        self.statusBar().showMessage(tr("status.dialect_switched", dialect=dialect.upper()))

    def _on_viewport_face_selected(self, face_id: str) -> None:
        if face_id:
            self.tree_dock.select_face_by_id(face_id)
            face = self.project.get_face_by_id(face_id)
            if face is not None:
                self.statusBar().showMessage(
                    tr(
                        "status.inspecting_face",
                        label=face.format_label(get_language()),
                        z_max=face.z_max,
                        z_min=face.z_min,
                    )
                )

    def action_assign_operation_to_face(self, face_id: str, op_type: object) -> None:
        if not isinstance(op_type, OperationType):
            return
        face = self.project.get_face_by_id(face_id)
        if face is None:
            return
        new_op = self.project.create_operation_for_face(face, op_type)
        self._active_op_id = new_op.op_id
        self.project.recalculate_all()
        self.tree_dock.refresh()
        self.props_dock._populate_face_combo()
        self.props_dock.inspect_operation(new_op)
        self.props_dock.update_simulation_labels()
        self.gcode_dock.set_gcode(self.project.gcode_text)
        self.tree_dock.select_operation_by_id(new_op.op_id)
        self.viewport.select_face(face.face_id, emit_signal=False)
        self.viewport.render_project(self.project, active_op_id=new_op.op_id)
        self.statusBar().showMessage(
            tr("status.inspecting", name=new_op.name, tool_id=new_op.tool_id, count=len(new_op.commands))
        )

    def _on_tree_node_selected(self, node_kind: str, node_id: str) -> None:
        if node_kind == "operation":
            self._active_op_id = node_id
            op = next((o for o in self.project.operations if o.op_id == node_id), None)
            self.props_dock.inspect_operation(op)
            if op is not None:
                face_id = op.assigned_face_id if op.geometry_scope == "face" else None
                self.viewport.select_face(face_id, emit_signal=False)
                self.statusBar().showMessage(
                    tr("status.inspecting", name=op.name, tool_id=op.tool_id, count=len(op.commands))
                )
        elif node_kind == "face":
            self._active_op_id = None
            self.viewport.select_face(node_id, emit_signal=False)
            face = self.project.get_face_by_id(node_id)
            if face is not None:
                self.statusBar().showMessage(
                    tr(
                        "status.inspecting_face",
                        label=face.format_label(get_language()),
                        z_max=face.z_max,
                        z_min=face.z_min,
                    )
                )
        else:
            self._active_op_id = None
            self.viewport.select_face(None, emit_signal=False)
            self.props_dock.inspect_operation(None)
            self.statusBar().showMessage(tr("status.showing_all", name=self.project.name))

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
        self.statusBar().showMessage(tr("status.demo_loaded"))

    def action_open_project(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open LatheCAM Project (.lcam)",
            "",
            "LatheCAM Project (*.lcam);;All Files (*)",
        )
        if not filepath:
            return
        try:
            self.project = LatheProject.load_from_file(filepath)
            self._active_op_id = None
            self._sync_all_views()
            self.statusBar().showMessage(tr("status.project_loaded", path=filepath))
        except Exception as exc:
            QMessageBox.critical(self, "Project Load Error", f"Failed to load {filepath}:\n{exc}")

    def action_save_project(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save LatheCAM Project (.lcam)",
            f"{self.project.name.lower().replace(' ', '_')}.lcam",
            "LatheCAM Project (*.lcam);;All Files (*)",
        )
        if not filepath:
            return
        try:
            self.project.save_to_file(filepath)
            self.statusBar().showMessage(tr("status.project_saved", path=filepath))
        except Exception as exc:
            QMessageBox.critical(self, "Project Save Error", f"Failed to save {filepath}:\n{exc}")

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
            self.statusBar().showMessage(
                tr("status.cad_imported", name=path.name, count=len(contour.points))
            )
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
        is_fanuc = self.project.post_dialect == "fanuc"
        ext = ".nc" if is_fanuc else ".ngc"
        filter_str = "Fanuc G-Code (*.nc);;All Files (*)" if is_fanuc else "LinuxCNC G-Code (*.ngc);;All Files (*)"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            f"Export G-Code ({ext})",
            f"{self.project.name.lower().replace(' ', '_')}{ext}",
            filter_str,
        )
        if not filepath:
            return
        Path(filepath).write_text(self.project.gcode_text, encoding="utf-8")
        self.statusBar().showMessage(tr("status.gcode_exported", path=filepath))

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
