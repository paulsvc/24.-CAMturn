from __future__ import annotations

import math
from typing import Sequence
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lathecam.cad.geometry import Point2D
from lathecam.cam.simulator import discretize_arc
from lathecam.models.project import LatheProject
from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_viewport_colors
from lathecam.ui.viewport.base_canvas import BaseViewportCanvas


def build_revolved_mesh(
    profile_pts: Sequence[Point2D],
    start_deg: float = 75.0,
    end_deg: float = 360.0,
    n_theta: int = 64,
) -> pv.PolyData:
    """Revolves a 2D (Z_axial, X_radius) profile around the spindle axis into a 3D PyVista mesh.
    
    Coordinate mapping in VTK 3D space:
    - VTK X = Lathe Z_axial (horizontal spindle axis)
    - VTK Y = Lathe X_radius * sin(theta)
    - VTK Z = Lathe X_radius * cos(theta) (so theta=0 is the vertical +Z plane)
    """
    pts = list(profile_pts)
    if pts[0][0] < pts[-1][0]:
        pts.reverse()

    # Close profile down to spindle centerline (X_radius = 0)
    closed_pts: list[Point2D] = [(pts[0][0], 0.0)]
    closed_pts.extend(pts)
    closed_pts.append((pts[-1][0], 0.0))

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
    """Hardware-accelerated PyVista / VTK 3D & 2D interactive lathe viewport."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._project: LatheProject | None = None
        self._active_op_id: str | None = None
        self.show_stock: bool = True
        self.show_simulated_cut: bool = False
        self.is_2d_mode: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top HUD bar for quick viewport controls and color legend
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

        self.btn_toggle_stock = QPushButton(tr("viewport.btn_stock_on"))
        self.btn_toggle_stock.setObjectName("secondaryBtn")
        self.btn_toggle_stock.clicked.connect(self._toggle_stock)

        self.btn_toggle_sim = QPushButton(tr("viewport.btn_sim_off"))
        self.btn_toggle_sim.setObjectName("secondaryBtn")
        self.btn_toggle_sim.clicked.connect(self._toggle_sim)

        hud_layout.addWidget(self.btn_iso)
        hud_layout.addWidget(self.btn_zx)
        hud_layout.addWidget(self.btn_toggle_stock)
        hud_layout.addWidget(self.btn_toggle_sim)
        hud_layout.addStretch()

        self.lbl_legend = QLabel(tr("viewport.legend"))
        hud_layout.addWidget(self.lbl_legend)
        layout.addWidget(self.hud_bar)

        # VTK Interactor
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)

        self.apply_theme_colors()

    def apply_theme_colors(self) -> None:
        colors = get_viewport_colors()
        self.hud_bar.setStyleSheet(
            f"background-color: {colors['hud_bg']}; border-bottom: 1px solid {colors['hud_border']};"
        )
        self.plotter.set_background(colors["bg_bottom"], top=colors["bg_top"])
        self.plotter.add_axes(
            xlabel="Z (Spindle)",
            ylabel="Y",
            zlabel="X (Radius)",
            color=colors["axes_color"],
        )
        if self._project is not None:
            self._rebuild_scene(reset_camera=False)

    def retranslate_ui(self) -> None:
        self.btn_iso.setText(tr("viewport.btn_iso"))
        self.btn_zx.setText(tr("viewport.btn_zx"))
        self.btn_toggle_stock.setText(
            tr("viewport.btn_stock_on") if self.show_stock else tr("viewport.btn_stock_off")
        )
        self.btn_toggle_sim.setText(
            tr("viewport.btn_sim_on") if self.show_simulated_cut else tr("viewport.btn_sim_off")
        )
        self.lbl_legend.setText(tr("viewport.legend"))

    def render_project(
        self,
        project: LatheProject,
        active_op_id: str | None = None,
    ) -> None:
        self._project = project
        self._active_op_id = active_op_id
        self._rebuild_scene(reset_camera=(self.plotter.renderer.GetActors().GetNumberOfItems() == 0))

    def _rebuild_scene(self, reset_camera: bool = False) -> None:
        if self._project is None:
            return

        colors = get_viewport_colors()
        self.plotter.clear_actors()

        st = self._project.stock
        contour_pts = self._project.contour.points

        # 1. Render 3D Revolved Part Solid (or 3D Simulated Cut Stock)
        if not self.is_2d_mode:
            if self.show_simulated_cut and self._project.shadowed_polygon is not None:
                from lathecam.cam.shadowing import extract_upper_profile
                sim_pts = extract_upper_profile(self._project.shadowed_polygon, sample_step_mm=0.35)
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
        profile_3d_closed = [(contour_pts[0][0], 0.0, 0.0)] + profile_3d + [(contour_pts[-1][0], 0.0, 0.0)]
        prof_line = build_polyline_polydata(profile_3d_closed)
        if prof_line is not None:
            self.plotter.add_mesh(prof_line, color=colors["profile_line"], line_width=3.0)

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
