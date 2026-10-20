from __future__ import annotations

import math
from typing import Sequence
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from lathecam.cad.face import FaceType, TurnedFace
from lathecam.cad.geometry import Point2D
from lathecam.cam.simulator import discretize_arc
from lathecam.cam.tool_mesh import SimFrame, build_simulation_trajectory, build_tool_3d_meshes
from lathecam.models.project import LatheProject, OperationType
from lathecam.ui.i18n import get_language, tr
from lathecam.ui.theme import get_current_theme, get_viewport_colors
from lathecam.ui.viewport.base_canvas import BaseViewportCanvas


def build_revolved_mesh(
    profile_pts: Sequence[Point2D],
    start_deg: float = 75.0,
    end_deg: float = 360.0,
    n_theta: int = 64,
    close_to_centerline: bool = True,
) -> pv.PolyData:
    """Revolves a 2D (Z_axial, X_radius) profile around the spindle axis into a 3D PyVista mesh.
    
    Coordinate mapping in VTK 3D space:
    - VTK X = Lathe Z_axial (horizontal spindle axis)
    - VTK Y = Lathe X_radius * sin(theta)
    - VTK Z = Lathe X_radius * cos(theta) (so theta=0 is the vertical +Z plane)
    """
    pts = list(profile_pts)
    is_closed = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-3
    if not is_closed and pts[0][0] < pts[-1][0]:
        pts.reverse()

    if close_to_centerline and not is_closed:
        closed_pts: list[Point2D] = []
        if abs(pts[0][1]) > 1e-4:
            closed_pts.append((pts[0][0], 0.0))
        closed_pts.extend(pts)
        if abs(pts[-1][1]) > 1e-4:
            closed_pts.append((pts[-1][0], 0.0))
    else:
        closed_pts = pts

    z_arr = np.array([p[0] for p in closed_pts], dtype=np.float64)
    r_arr = np.array([max(0.0, p[1]) for p in closed_pts], dtype=np.float64)
    thetas = np.linspace(math.radians(start_deg), math.radians(end_deg), n_theta)

    # Create 2D surface grid (n_theta x n_pts)
    theta_grid, z_grid = np.meshgrid(thetas, z_arr, indexing="ij")
    _, r_grid = np.meshgrid(thetas, r_arr, indexing="ij")

    vtk_x = z_grid
    vtk_y = r_grid * np.sin(theta_grid)
    vtk_z = r_grid * np.cos(theta_grid)

    grid = pv.StructuredGrid(vtk_x, vtk_y, vtk_z)
    surf = grid.extract_surface(algorithm="dataset_surface").triangulate().clean()
    surf.compute_normals(inplace=True, auto_orient_normals=True)
    return surf


def build_polyline_polydata(points_3d: Sequence[tuple[float, float, float]]) -> pv.PolyData | None:
    """Builds a VTK PolyData line strip from 3D coordinates."""
    if len(points_3d) < 2:
        return None
    pts_np = np.array(points_3d, dtype=np.float64)
    n_pts = len(pts_np)
    cells = np.empty((n_pts - 1, 3), dtype=np.int64)
    cells[:, 0] = 2
    cells[:, 1] = np.arange(0, n_pts - 1, dtype=np.int64)
    cells[:, 2] = np.arange(1, n_pts, dtype=np.int64)
    mesh = pv.PolyData(pts_np)
    mesh.lines = cells.ravel()
    return mesh


class VTKLatheViewport(BaseViewportCanvas):
    """Hardware-accelerated PyVista / VTK 3D & 2D interactive lathe viewport with Face Picking."""

    face_selected = Signal(str)  # face_id (or "" when cleared)
    assign_op_to_face_requested = Signal(str, object)  # (face_id, OperationType)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._project: LatheProject | None = None
        self._active_op_id: str | None = None
        self._active_face_id: str | None = None
        self.show_stock: bool = True
        self.show_simulated_cut: bool = False
        self.is_2d_mode: bool = False
        self.face_pick_enabled: bool = True

        # Tool simulation state
        self._sim_trajectory: list[SimFrame] = []
        self._sim_frame_idx: int = 0
        self._sim_timer: QTimer = QTimer(self)
        self._sim_timer.setInterval(25)
        self._sim_timer.timeout.connect(self._on_sim_timer_tick)
        self._sim_playing: bool = False
        self._sim_speed: float = 1.0
        self._tool_actors: dict[int, tuple[object, object]] = {}
        self._active_tool_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top HUD bar for quick viewport controls and color legend
        self.hud_bar = QWidget()
        hud_layout = QHBoxLayout(self.hud_bar)
        hud_layout.setContentsMargins(10, 4, 10, 4)
        hud_layout.setSpacing(8)

        self.btn_iso = QPushButton(tr("viewport.btn_iso"))
        self.btn_iso.setObjectName("secondaryBtn")
        self.btn_iso.clicked.connect(self.set_isometric_view)

        self.btn_zx = QPushButton(tr("viewport.btn_zx"))
        self.btn_zx.setObjectName("secondaryBtn")
        self.btn_zx.clicked.connect(self.set_zx_plane_view)

        self.btn_pick_face = QPushButton(tr("viewport.btn_pick_on"))
        self.btn_pick_face.setObjectName("secondaryBtn")
        self.btn_pick_face.clicked.connect(self._toggle_face_pick)

        self.btn_toggle_stock = QPushButton(tr("viewport.btn_stock_on"))
        self.btn_toggle_stock.setObjectName("secondaryBtn")
        self.btn_toggle_stock.clicked.connect(self._toggle_stock)

        self.btn_toggle_sim = QPushButton(tr("viewport.btn_sim_off"))
        self.btn_toggle_sim.setObjectName("secondaryBtn")
        self.btn_toggle_sim.clicked.connect(self._toggle_sim)

        hud_layout.addWidget(self.btn_iso)
        hud_layout.addWidget(self.btn_zx)
        hud_layout.addWidget(self.btn_pick_face)
        hud_layout.addWidget(self.btn_toggle_stock)
        hud_layout.addWidget(self.btn_toggle_sim)
        hud_layout.addStretch()

        self.lbl_legend = QLabel(tr("viewport.legend"))
        hud_layout.addWidget(self.lbl_legend)
        layout.addWidget(self.hud_bar)

        # 2. Contextual Face Action Bar (Shown when a CAD Face is selected)
        self.face_bar = QWidget()
        face_layout = QHBoxLayout(self.face_bar)
        face_layout.setContentsMargins(10, 5, 10, 5)
        face_layout.setSpacing(6)

        self.lbl_selected_face = QLabel("🎯 Face Selected")
        self.lbl_selected_face.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 12px;")
        face_layout.addWidget(self.lbl_selected_face)
        face_layout.addStretch()

        self.btn_face_rough = QPushButton(tr("face.act_rough"))
        self.btn_face_rough.clicked.connect(lambda: self._request_face_op(OperationType.ROUGHING))
        face_layout.addWidget(self.btn_face_rough)

        self.btn_face_finish = QPushButton(tr("face.act_finish"))
        self.btn_face_finish.clicked.connect(lambda: self._request_face_op(OperationType.FINISHING))
        face_layout.addWidget(self.btn_face_finish)

        self.btn_face_thread = QPushButton(tr("face.act_thread"))
        self.btn_face_thread.clicked.connect(lambda: self._request_face_op(OperationType.THREADING))
        face_layout.addWidget(self.btn_face_thread)

        self.btn_face_part = QPushButton(tr("face.act_part"))
        self.btn_face_part.clicked.connect(lambda: self._request_face_op(OperationType.PARTING))
        face_layout.addWidget(self.btn_face_part)

        self.btn_face_clear = QPushButton("✕")
        self.btn_face_clear.setObjectName("secondaryBtn")
        self.btn_face_clear.setFixedWidth(30)
        self.btn_face_clear.clicked.connect(lambda: self.select_face(None))
        face_layout.addWidget(self.btn_face_clear)

        self.face_bar.setVisible(False)
        layout.addWidget(self.face_bar)

        # 3. VTK Interactor
        self.plotter = QtInteractor(self)
        self.plotter.interactor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.plotter.interactor.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.plotter.interactor)

        # 4. Simulation Playback Control Bar
        self._setup_sim_bar(layout)

        self._setup_vtk_picking()
        self.apply_theme_colors()

    def _setup_sim_bar(self, layout: QVBoxLayout) -> None:
        """Constructs the interactive simulation timeline and playback toolbar."""
        self.sim_bar = QWidget()
        sim_layout = QHBoxLayout(self.sim_bar)
        sim_layout.setContentsMargins(10, 5, 10, 5)
        sim_layout.setSpacing(8)

        self.btn_sim_play = QPushButton(tr("sim.btn_play"))
        self.btn_sim_play.setFixedWidth(78)
        self.btn_sim_play.clicked.connect(self.sim_toggle_play_pause)

        self.btn_sim_stop = QPushButton(tr("sim.btn_stop"))
        self.btn_sim_stop.setObjectName("secondaryBtn")
        self.btn_sim_stop.setFixedWidth(72)
        self.btn_sim_stop.clicked.connect(self.sim_stop)

        self.btn_sim_step_back = QPushButton("⏮")
        self.btn_sim_step_back.setObjectName("secondaryBtn")
        self.btn_sim_step_back.setFixedWidth(36)
        self.btn_sim_step_back.setToolTip(tr("sim.step_back"))
        self.btn_sim_step_back.clicked.connect(lambda: self.sim_step(-15))

        self.btn_sim_step_fwd = QPushButton("⏭")
        self.btn_sim_step_fwd.setObjectName("secondaryBtn")
        self.btn_sim_step_fwd.setFixedWidth(36)
        self.btn_sim_step_fwd.setToolTip(tr("sim.step_fwd"))
        self.btn_sim_step_fwd.clicked.connect(lambda: self.sim_step(15))

        self.slider_sim = QSlider(Qt.Orientation.Horizontal)
        self.slider_sim.setRange(0, 0)
        self.slider_sim.setValue(0)
        self.slider_sim.sliderMoved.connect(self._on_slider_moved)
        self.slider_sim.valueChanged.connect(self._on_slider_value_changed)

        self.lbl_sim_status = QLabel("G0 RAPID")
        self.lbl_sim_status.setStyleSheet(
            "background-color: #dc2626; color: #ffffff; border-radius: 4px; padding: 2px 7px; font-weight: bold; font-size: 11px;"
        )

        self.lbl_sim_tool = QLabel("T1")
        self.lbl_sim_tool.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")

        self.lbl_sim_pos = QLabel("Z: +0.000  X: +0.000 (Ø0.000)")
        self.lbl_sim_pos.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold;")

        self.combo_sim_speed = QComboBox()
        self.combo_sim_speed.addItems(["0.5x", "1.0x", "2.0x", "4.0x", "8.0x"])
        self.combo_sim_speed.setCurrentText("1.0x")
        self.combo_sim_speed.currentTextChanged.connect(self._on_speed_changed)
        self.combo_sim_speed.setFixedWidth(68)

        sim_layout.addWidget(self.btn_sim_play)
        sim_layout.addWidget(self.btn_sim_stop)
        sim_layout.addWidget(self.btn_sim_step_back)
        sim_layout.addWidget(self.btn_sim_step_fwd)
        sim_layout.addWidget(self.slider_sim)
        sim_layout.addWidget(self.lbl_sim_status)
        sim_layout.addWidget(self.lbl_sim_tool)
        sim_layout.addWidget(self.lbl_sim_pos)
        sim_layout.addWidget(self.combo_sim_speed)
        layout.addWidget(self.sim_bar)

    def _setup_vtk_picking(self) -> None:
        """Enables left-click surface point picking on the VTK scene to select TurnedFace features."""
        try:
            self.plotter.enable_point_picking(
                callback=self._on_vtk_point_picked,
                show_message=False,
                show_point=False,
                left_clicking=True,
                use_picker=True,
            )
        except Exception:
            pass

    def _on_vtk_point_picked(self, picked_pt: Sequence[float] | None, *args: object) -> None:
        if not self.face_pick_enabled or self._project is None or picked_pt is None:
            return
        if len(picked_pt) < 3:
            return
        vtk_x, vtk_y, vtk_z = float(picked_pt[0]), float(picked_pt[1]), float(picked_pt[2])
        lathe_z = vtk_x
        lathe_r = abs(vtk_z) if self.is_2d_mode else math.hypot(vtk_y, vtk_z)

        best_face: TurnedFace | None = None
        best_dist = float("inf")
        for face in self._project.faces:
            d = face.distance_to_point(lathe_z, lathe_r)
            if d < best_dist:
                best_dist = d
                best_face = face

        if best_face is not None and best_dist <= 8.0:
            self.select_face(best_face.face_id)

    def select_face(self, face_id: str | None, emit_signal: bool = True) -> None:
        self._active_face_id = face_id
        face = self._project.get_face_by_id(face_id) if self._project else None
        if face is not None:
            self.face_bar.setVisible(True)
            self.lbl_selected_face.setText(
                f"{face.icon} {face.format_label(get_language())}  [Z: {face.z_max:.1f} → {face.z_min:.1f} mm]"
            )
            self.btn_face_thread.setEnabled(face.face_type in (FaceType.CYLINDER, FaceType.TAPER))
        else:
            self.face_bar.setVisible(False)

        self._rebuild_scene(reset_camera=False)
        if emit_signal:
            self.face_selected.emit(face_id or "")

    def _request_face_op(self, op_type: OperationType) -> None:
        if self._active_face_id:
            self.assign_op_to_face_requested.emit(self._active_face_id, op_type)

    def _on_context_menu(self, pos: QPoint) -> None:
        if self._project is None or not self._project.faces:
            return
        face = self._project.get_face_by_id(self._active_face_id) or self._project.faces[1]
        menu = QMenu(self)
        hdr = QAction(tr("face.menu_header", label=face.format_label(get_language())), self)
        hdr.setEnabled(False)
        menu.addAction(hdr)
        menu.addSeparator()

        act_rough = menu.addAction(tr("face.act_rough"))
        act_finish = menu.addAction(tr("face.act_finish"))
        act_thread = menu.addAction(tr("face.act_thread"))
        act_part = menu.addAction(tr("face.act_part"))
        menu.addSeparator()
        act_clear = menu.addAction(tr("face.act_clear"))

        chosen = menu.exec(self.plotter.interactor.mapToGlobal(pos))
        if chosen == act_rough:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.ROUGHING)
        elif chosen == act_finish:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.FINISHING)
        elif chosen == act_thread:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.THREADING)
        elif chosen == act_part:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.PARTING)
        elif chosen == act_clear:
            self.select_face(None)

    def apply_theme_colors(self) -> None:
        colors = get_viewport_colors()
        is_light = get_current_theme() == "light"
        self.hud_bar.setStyleSheet(
            f"background-color: {colors['hud_bg']}; border-bottom: 1px solid {colors['hud_border']};"
        )
        face_bar_bg = "#fef3c7" if is_light else "#292218"
        face_bar_border = "#f59e0b"
        lbl_color = "#b45309" if is_light else "#fbbf24"
        self.face_bar.setStyleSheet(
            f"background-color: {face_bar_bg}; border-bottom: 2px solid {face_bar_border};"
        )
        self.lbl_selected_face.setStyleSheet(f"color: {lbl_color}; font-weight: bold; font-size: 12px;")

        self.plotter.set_background(colors["bg_bottom"], top=colors["bg_top"])
        self.plotter.add_axes(
            xlabel="Z (Spindle)",
            ylabel="Y",
            zlabel="X (Radius)",
            color=colors["axes_color"],
        )
        sim_bg = "#f1f5f9" if is_light else "#0f172a"
        sim_border = "#cbd5e1" if is_light else "#334155"
        pos_color = "#0f172a" if is_light else "#f8fafc"
        self.sim_bar.setStyleSheet(f"background-color: {sim_bg}; border-top: 1px solid {sim_border};")
        self.lbl_sim_pos.setStyleSheet(f"color: {pos_color}; font-family: monospace; font-size: 11px; font-weight: bold;")
        if self._project is not None:
            self._rebuild_scene(reset_camera=False)

    def retranslate_ui(self) -> None:
        self.btn_iso.setText(tr("viewport.btn_iso"))
        self.btn_zx.setText(tr("viewport.btn_zx"))
        self.btn_pick_face.setText(
            tr("viewport.btn_pick_on") if self.face_pick_enabled else tr("viewport.btn_pick_off")
        )
        self.btn_toggle_stock.setText(
            tr("viewport.btn_stock_on") if self.show_stock else tr("viewport.btn_stock_off")
        )
        self.btn_toggle_sim.setText(
            tr("viewport.btn_sim_on") if self.show_simulated_cut else tr("viewport.btn_sim_off")
        )
        self.lbl_legend.setText(tr("viewport.legend"))
        self.btn_face_rough.setText(tr("face.act_rough"))
        self.btn_face_finish.setText(tr("face.act_finish"))
        self.btn_face_thread.setText(tr("face.act_thread"))
        self.btn_face_part.setText(tr("face.act_part"))

        self.btn_sim_play.setText(tr("sim.btn_pause") if self._sim_playing else tr("sim.btn_play"))
        self.btn_sim_stop.setText(tr("sim.btn_stop"))
        self.btn_sim_step_back.setToolTip(tr("sim.step_back"))
        self.btn_sim_step_fwd.setToolTip(tr("sim.step_fwd"))

        if self._active_face_id and self._project:
            face = self._project.get_face_by_id(self._active_face_id)
            if face is not None:
                self.lbl_selected_face.setText(
                    f"{face.icon} {face.format_label(get_language())}  [Z: {face.z_max:.1f} → {face.z_min:.1f} mm]"
                )

    def render_project(
        self,
        project: LatheProject,
        active_op_id: str | None = None,
    ) -> None:
        self._project = project
        self._active_op_id = active_op_id

        if self._sim_playing:
            self.sim_pause()

        self._sim_trajectory = build_simulation_trajectory(self._project, op_id=self._active_op_id)
        self._sim_frame_idx = 0
        self.slider_sim.blockSignals(True)
        self.slider_sim.setRange(0, max(0, len(self._sim_trajectory) - 1))
        self.slider_sim.setValue(0)
        self.slider_sim.blockSignals(False)

        self._rebuild_scene(reset_camera=(self.plotter.renderer.GetActors().GetNumberOfItems() == 0))

    def sim_play(self) -> None:
        """Starts continuous simulation playback along the toolpath."""
        if not self._sim_trajectory:
            return
        if self._sim_frame_idx >= len(self._sim_trajectory) - 1:
            self._sim_frame_idx = 0
            self._apply_sim_frame(0)
        self._sim_playing = True
        self.btn_sim_play.setText(tr("sim.btn_pause"))
        self._sim_timer.start(25)

    def sim_pause(self) -> None:
        """Pauses simulation playback at the current frame."""
        self._sim_playing = False
        self._sim_timer.stop()
        self.btn_sim_play.setText(tr("sim.btn_play"))

    def sim_stop(self) -> None:
        """Stops simulation and rewinds the tool to the beginning."""
        self.sim_pause()
        self._sim_frame_idx = 0
        if self._sim_trajectory:
            self._apply_sim_frame(0)

    def sim_toggle_play_pause(self) -> None:
        """Toggles between Play and Pause states."""
        if self._sim_playing:
            self.sim_pause()
        else:
            self.sim_play()

    def sim_step(self, delta_frames: int) -> None:
        """Steps forward or backward by a given number of frames."""
        if not self._sim_trajectory:
            return
        self.sim_pause()
        new_idx = max(0, min(self._sim_frame_idx + delta_frames, len(self._sim_trajectory) - 1))
        self._apply_sim_frame(new_idx)

    def _on_slider_moved(self, val: int) -> None:
        if self._sim_playing:
            self.sim_pause()
        self._apply_sim_frame(val)

    def _on_slider_value_changed(self, val: int) -> None:
        if not self._sim_playing:
            self._apply_sim_frame(val)

    def _on_speed_changed(self, text: str) -> None:
        try:
            self._sim_speed = float(text.replace("x", "").strip())
        except ValueError:
            self._sim_speed = 1.0

    def _on_sim_timer_tick(self) -> None:
        if not self._sim_trajectory:
            self.sim_pause()
            return
        step = max(1, int(round(self._sim_speed * 3)))
        next_idx = self._sim_frame_idx + step
        if next_idx >= len(self._sim_trajectory):
            self._apply_sim_frame(len(self._sim_trajectory) - 1)
            self.sim_pause()
        else:
            self._apply_sim_frame(next_idx)

    def _apply_sim_frame(self, idx: int, render: bool = True) -> None:
        if not self._sim_trajectory:
            return
        idx = max(0, min(idx, len(self._sim_trajectory) - 1))
        self._sim_frame_idx = idx
        frame = self._sim_trajectory[idx]

        # Update slider without recursive trigger
        self.slider_sim.blockSignals(True)
        self.slider_sim.setValue(idx)
        self.slider_sim.blockSignals(False)

        # Switch tool visibility if needed
        if frame.tool_id != self._active_tool_id:
            for tid, (ins_act, shk_act) in self._tool_actors.items():
                ins_act.SetVisibility(tid == frame.tool_id)
                shk_act.SetVisibility(tid == frame.tool_id)
            self._active_tool_id = frame.tool_id

        # Update position of active tool
        if frame.tool_id in self._tool_actors:
            ins_act, shk_act = self._tool_actors[frame.tool_id]
            ins_act.SetPosition(frame.z, 0.0, frame.x)
            shk_act.SetPosition(frame.z, 0.0, frame.x)

        # Update UI readouts
        dia = frame.x * 2.0
        self.lbl_sim_pos.setText(f"Z: {frame.z:+7.3f}  X: {frame.x:6.3f} (Ø{dia:6.3f})")
        self.lbl_sim_tool.setText(f"T{frame.tool_id} {frame.tool_name}")
        self._update_status_badge(frame.mode)

        if render:
            self.plotter.render()

    def _update_status_badge(self, mode: str) -> None:
        m = (mode or "").upper()
        if m == "G0":
            bg = "#dc2626"
            text = "G0 RAPID"
        elif m in ("G1", "G41", "G42", "G40"):
            bg = "#16a34a"
            text = "G1 FEED"
        elif m in ("G2", "G3"):
            bg = "#0891b2"
            text = f"{m} ARC"
        elif m in ("G33", "G76"):
            bg = "#ca8a04"
            text = f"{m} THREAD"
        elif m in ("G83", "G73"):
            bg = "#9333ea"
            text = f"{m} PECK"
        else:
            bg = "#64748b"
            text = m
        self.lbl_sim_status.setStyleSheet(
            f"background-color: {bg}; color: #ffffff; border-radius: 4px; padding: 2px 7px; font-weight: bold; font-size: 11px;"
        )
        self.lbl_sim_status.setText(text)

    def _rebuild_scene(self, reset_camera: bool = False) -> None:
        if self._project is None:
            return

        colors = get_viewport_colors()
        self.plotter.clear_actors()

        st = self._project.stock
        contour_pts = self._project.contour.points
        selected_face = self._project.get_face_by_id(self._active_face_id)

        # 1. Render 3D Revolved Part Solid (or 3D Simulated Cut Stock)
        if not self.is_2d_mode:
            if self.show_simulated_cut and self._project.simulation_result is not None:
                from lathecam.cam.shadowing import extract_upper_profile
                sim_pts = extract_upper_profile(self._project.simulation_result.remaining_stock, sample_step_mm=0.35)
                if len(sim_pts) >= 2:
                    sim_mesh = build_revolved_mesh(sim_pts, start_deg=70.0, end_deg=355.0)
                    self.plotter.add_mesh(
                        sim_mesh,
                        color=colors["sim_mesh"],
                        specular=0.65,
                        specular_power=30,
                        smooth_shading=True,
                        opacity=0.94,
                    )
            else:
                part_mesh = build_revolved_mesh(contour_pts, start_deg=75.0, end_deg=355.0)
                self.plotter.add_mesh(
                    part_mesh,
                    color=colors["part_mesh"],
                    specular=0.65,
                    specular_power=30,
                    smooth_shading=True,
                    opacity=0.95,
                )

            # 1b. If a CAD Face is selected, render a 3D glowing gold/amber surface band on that face
            if selected_face is not None and len(selected_face.points) >= 2:
                face_pts_offset = [(z, r + 0.08) for z, r in selected_face.points]
                face_mesh_3d = build_revolved_mesh(
                    face_pts_offset,
                    start_deg=70.0,
                    end_deg=358.0,
                    n_theta=48,
                    close_to_centerline=False,
                )
                self.plotter.add_mesh(
                    face_mesh_3d,
                    color="#f59e0b",
                    specular=0.85,
                    specular_power=40,
                    smooth_shading=True,
                    opacity=0.92,
                )

            # 2. Render Translucent 3D Stock Cylinder Envelope
            if self.show_stock:
                stock_pts: list[Point2D] = [
                    (st.z_start_mm, st.od_radius),
                    (st.z_end_mm, st.od_radius),
                ]
                stock_mesh = build_revolved_mesh(stock_pts, start_deg=110.0, end_deg=340.0, n_theta=48)
                self.plotter.add_mesh(
                    stock_mesh,
                    color=colors["stock_mesh"],
                    opacity=0.18,
                    smooth_shading=True,
                )

        # 3. Render 2D Upper-Half Meridian Part Profile & Stock Wireframe on Y=0 Plane
        profile_3d = [(z, 0.0, x) for z, x in contour_pts]
        if self._project.contour.is_closed:
            prof_line = build_polyline_polydata(profile_3d)
        else:
            profile_3d_closed = [(contour_pts[0][0], 0.0, 0.0)] + profile_3d + [(contour_pts[-1][0], 0.0, 0.0)]
            prof_line = build_polyline_polydata(profile_3d_closed)
        if prof_line is not None:
            self.plotter.add_mesh(prof_line, color=colors["profile_line"], line_width=3.0)

        # 3b. Render Highlighted 2D Segment on Y=0 Plane for the Selected Face
        if selected_face is not None and len(selected_face.points) >= 2:
            sel_3d = [(z, 0.0, x) for z, x in selected_face.points]
            sel_line = build_polyline_polydata(sel_3d)
            if sel_line is not None:
                self.plotter.add_mesh(sel_line, color="#f59e0b", line_width=7.0)

        if self.show_stock:
            stock_wire_3d = [
                (st.z_start_mm, 0.0, 0.0),
                (st.z_start_mm, 0.0, st.od_radius),
                (st.z_end_mm, 0.0, st.od_radius),
                (st.z_end_mm, 0.0, 0.0),
            ]
            stock_line = build_polyline_polydata(stock_wire_3d)
            if stock_line is not None:
                self.plotter.add_mesh(stock_line, color=colors["stock_wire"], line_width=1.5)

        # Centerline axis (X_radius = 0)
        centerline_3d = [
            (st.z_end_mm - 4.0, 0.0, 0.0),
            (st.z_start_mm + 6.0, 0.0, 0.0),
        ]
        cl_mesh = build_polyline_polydata(centerline_3d)
        if cl_mesh is not None:
            self.plotter.add_mesh(cl_mesh, color=colors["centerline"], line_width=1.2)

        # 4. Render Toolpaths (Filtered by active operation if selected, else all enabled operations)
        ops_to_draw = [
            op for op in self._project.operations
            if op.enabled and (self._active_op_id is None or op.op_id == self._active_op_id)
        ]

        g0_segments: list[list[tuple[float, float, float]]] = []
        g1_segments: list[list[tuple[float, float, float]]] = []
        arc_segments: list[list[tuple[float, float, float]]] = []
        thread_segments: list[list[tuple[float, float, float]]] = []

        for op in ops_to_draw:
            cur_z = st.z_start_mm + 2.0
            cur_x = st.od_radius + 2.0

            for cmd in op.preview_commands:
                if cmd.mode == "COMMENT":
                    continue
                target_z = cmd.z if cmd.z is not None else cur_z
                target_x = cmd.x if cmd.x is not None else cur_x

                p_start = (cur_z, 0.0, cur_x)
                p_end = (target_z, 0.0, target_x)

                if cmd.mode == "G0":
                    g0_segments.append([p_start, p_end])
                    cur_z, cur_x = target_z, target_x

                elif cmd.mode in ("G1", "G41", "G42", "G40"):
                    g1_segments.append([p_start, p_end])
                    cur_z, cur_x = target_z, target_x

                elif cmd.mode in ("G2", "G3") and cmd.i is not None and cmd.k is not None:
                    center = (cur_z + cmd.k, cur_x + cmd.i)
                    arc_2d = discretize_arc((cur_z, cur_x), (target_z, target_x), center, mode=cmd.mode)
                    arc_3d = [(pz, 0.0, px) for pz, px in arc_2d]
                    arc_segments.append(arc_3d)
                    cur_z, cur_x = target_z, target_x

                elif cmd.mode in ("G33", "G76"):
                    thread_segments.append([p_start, p_end])
                    cur_z, cur_x = target_z, target_x

                elif cmd.mode in ("G83", "G73"):
                    r_plane = cmd.raw_params.get("r_plane", 1.0) if cmd.raw_params else 1.0
                    g1_segments.append([(r_plane, 0.0, 0.0), (target_z, 0.0, 0.0)])
                    cur_z, cur_x = r_plane, 0.0

        self._add_batched_lines(g0_segments, colors["g0"], line_width=1.4)
        self._add_batched_lines(g1_segments, colors["g1"], line_width=2.4)
        self._add_batched_lines(arc_segments, colors["arc"], line_width=3.2)
        self._add_batched_lines(thread_segments, colors["thread"], line_width=2.2)

        # 5. Build and attach 3D tool actors
        self._tool_actors.clear()
        self._active_tool_id = None
        if self._project.tools:
            for tool in self._project.tools.values():
                ins_mesh, shk_mesh = build_tool_3d_meshes(tool)
                ins_act = self.plotter.add_mesh(
                    ins_mesh,
                    color="#f59e0b",
                    specular=0.85,
                    specular_power=40,
                    smooth_shading=True,
                )
                shk_act = self.plotter.add_mesh(
                    shk_mesh,
                    color="#334155",
                    specular=0.5,
                    specular_power=20,
                    smooth_shading=True,
                )
                ins_act.SetVisibility(False)
                shk_act.SetVisibility(False)
                self._tool_actors[tool.tool_id] = (ins_act, shk_act)
        else:
            ins_mesh, shk_mesh = build_tool_3d_meshes(None)
            ins_act = self.plotter.add_mesh(ins_mesh, color="#f59e0b", specular=0.85, smooth_shading=True)
            shk_act = self.plotter.add_mesh(shk_mesh, color="#334155", specular=0.5, smooth_shading=True)
            ins_act.SetVisibility(False)
            shk_act.SetVisibility(False)
            self._tool_actors[1] = (ins_act, shk_act)

        # Position tool at current simulation frame
        if self._sim_trajectory:
            self._apply_sim_frame(self._sim_frame_idx, render=False)

        if reset_camera:
            self.set_isometric_view()
        else:
            self.plotter.render()

    def _add_batched_lines(
        self,
        segments: Sequence[Sequence[tuple[float, float, float]]],
        color: str,
        line_width: float = 2.0,
    ) -> None:
        if not segments:
            return
        all_pts: list[tuple[float, float, float]] = []
        all_cells: list[int] = []
        idx_offset = 0
        for seg in segments:
            if len(seg) < 2:
                continue
            n = len(seg)
            all_pts.extend(seg)
            for k in range(n - 1):
                all_cells.extend([2, idx_offset + k, idx_offset + k + 1])
            idx_offset += n

        if not all_pts:
            return
        mesh = pv.PolyData(np.array(all_pts, dtype=np.float64))
        mesh.lines = np.array(all_cells, dtype=np.int64)
        self.plotter.add_mesh(mesh, color=color, line_width=line_width)

    def set_isometric_view(self) -> None:
        self.is_2d_mode = False
        self._rebuild_scene(reset_camera=False)
        self.plotter.disable_parallel_projection()
        self.plotter.camera_position = [
            (-16.0, -96.0, 56.0),   # Camera position looking at cutaway + X-Z plane
            (-21.0, 0.0, 6.0),      # Focal point
            (0.0, 0.0, 1.0),        # View up (+X_radius is vertical)
        ]
        self.plotter.render()

    def set_zx_plane_view(self) -> None:
        self.is_2d_mode = True
        self._rebuild_scene(reset_camera=False)
        self.plotter.enable_parallel_projection()
        self.plotter.camera_position = [
            (-21.0, -108.0, 10.0),  # Perpendicular to Y=0 (X-Z lathe plane)
            (-21.0, 0.0, 10.0),
            (0.0, 0.0, 1.0),
        ]
        self.plotter.camera.parallel_scale = 22.0
        self.plotter.render()

    def _toggle_face_pick(self) -> None:
        self.face_pick_enabled = not self.face_pick_enabled
        self.btn_pick_face.setText(
            tr("viewport.btn_pick_on") if self.face_pick_enabled else tr("viewport.btn_pick_off")
        )
        if not self.face_pick_enabled:
            self.select_face(None)

    def _toggle_stock(self) -> None:
        self.show_stock = not self.show_stock
        self.btn_toggle_stock.setText(
            tr("viewport.btn_stock_on") if self.show_stock else tr("viewport.btn_stock_off")
        )
        self._rebuild_scene(reset_camera=False)

    def _toggle_sim(self) -> None:
        self.show_simulated_cut = not self.show_simulated_cut
        self.btn_toggle_sim.setText(
            tr("viewport.btn_sim_on") if self.show_simulated_cut else tr("viewport.btn_sim_off")
        )
        self._rebuild_scene(reset_camera=False)
