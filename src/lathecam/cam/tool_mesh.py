from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence
import numpy as np
import pyvista as pv

from lathecam.cam.simulator import discretize_arc
from lathecam.cam.tools import LatheTool
from lathecam.models.project import LatheProject, OperationType


@dataclass
class SimFrame:
    """Represents a discrete simulation trajectory frame for toolpath playback."""
    z: float          # Lathe Z coordinate (mm)
    x: float          # Lathe X radius (mm)
    mode: str         # "G0", "G1", "G2", "G3", "G33", "G76", "G83", etc.
    tool_id: int      # Active tool ID
    tool_name: str    # Tool name / description
    op_name: str      # Associated operation name
    feed: float = 0.2 # Feed rate (mm/rev or mm/min)


def _make_prism_mesh(pts_2d: Sequence[tuple[float, float]], y_half: float) -> pv.PolyData:
    """Creates a 3D extruded prism mesh in VTK space:
    VTK X = Lathe Z (axial)
    VTK Y = Lateral thickness (from -y_half to +y_half)
    VTK Z = Lathe X (radial)
    """
    pts = np.asarray(pts_2d, dtype=np.float64)
    n = len(pts)
    v_bottom = np.column_stack([pts[:, 0], np.full(n, -y_half), pts[:, 1]])
    v_top = np.column_stack([pts[:, 0], np.full(n, y_half), pts[:, 1]])
    vertices = np.vstack([v_bottom, v_top])

    faces: list[int] = []
    # Bottom polygon (facing -Y)
    faces.extend([n] + list(range(n - 1, -1, -1)))
    # Top polygon (facing +Y)
    faces.extend([n] + list(range(n, 2 * n)))
    # Side quads
    for i in range(n):
        next_i = (i + 1) % n
        faces.extend([4, i, next_i, next_i + n, i + n])

    mesh = pv.PolyData(vertices, np.array(faces, dtype=np.int64)).triangulate().clean()
    mesh.compute_normals(inplace=True, auto_orient_normals=True)
    return mesh


def build_tool_3d_meshes(tool: LatheTool | None) -> tuple[pv.PolyData, pv.PolyData]:
    """Builds the 3D (Insert, Shank) PolyData meshes for a LatheTool.
    
    The cutting tip / origin is placed at (VTK X=0, VTK Y=0, VTK Z=0).
    In standard OD turning (Quadrant 3, tool on +X side):
    - Tool cuts toward chuck (-Lathe Z, i.e. -VTK X) and faces toward center (-Lathe X, i.e. -VTK Z).
    - Insert and toolholder extend into +Lathe Z (+VTK X) and +Lathe X (+VTK Z).
    
    Returns:
        tuple[pv.PolyData, pv.PolyData]: (insert_mesh, shank_mesh)
    """
    if tool is None:
        shape = "C"
        tip_w = 3.0
    else:
        shape = (tool.insert_shape or "C").upper()
        tip_w = max(1.0, tool.tip_width_mm)

    if shape == "DRILL":
        # Axial drill: points along -VTK X (into workpiece from front face)
        radius = max(1.0, tip_w / 2.0)
        cone_h = radius / math.tan(math.radians(59.0))  # 118 deg standard point angle
        # Cone apex at (0, 0, 0), base at cone_h
        cone = pv.Cone(
            center=(cone_h / 2.0, 0.0, 0.0),
            direction=(-1.0, 0.0, 0.0),
            radius=radius,
            height=cone_h,
            resolution=32,
        )
        cyl = pv.Cylinder(
            center=(cone_h + 18.0, 0.0, 0.0),
            direction=(1.0, 0.0, 0.0),
            radius=radius,
            height=36.0,
            resolution=32,
        )
        drill_body = (cone + cyl).triangulate().clean()
        drill_body.compute_normals(inplace=True)

        # Drill chuck / holder adapter
        chuck = pv.Cylinder(
            center=(cone_h + 36.0 + 10.0, 0.0, 0.0),
            direction=(1.0, 0.0, 0.0),
            radius=radius * 1.6,
            height=20.0,
            resolution=32,
        ).triangulate().clean()
        chuck.compute_normals(inplace=True)
        return drill_body, chuck

    elif shape == "PART":
        # Parting / Grooving blade
        w = tip_w
        # Blade insert
        insert_pts = [
            (0.0, 0.0),
            (0.0, 13.0),
            (w, 13.0),
            (w, 0.0),
        ]
        insert_mesh = _make_prism_mesh(insert_pts, y_half=min(1.4, w / 2.0))
        # Blade holder block
        shank_pts = [
            (-2.0, 9.0),
            (-2.0, 22.0),
            (w + 12.0, 22.0),
            (w + 12.0, 9.0),
        ]
        shank_mesh = _make_prism_mesh(shank_pts, y_half=6.0)
        return insert_mesh, shank_mesh

    elif shape == "THREAD":
        # 60-degree triangular threading insert
        insert_pts = [
            (0.0, 0.0),
            (-2.5, 4.33),
            (7.5, 4.33),
            (5.0, 0.0),
        ]
        insert_mesh = _make_prism_mesh(insert_pts, y_half=1.75)
        shank_pts = [
            (2.0, 3.5),
            (2.0, 20.0),
            (32.0, 20.0),
            (32.0, 3.5),
        ]
        shank_mesh = _make_prism_mesh(shank_pts, y_half=6.0)
        return insert_mesh, shank_mesh

    elif shape == "D":
        # DNMG 55-degree diamond finishing insert
        insert_pts = [
            (0.0, 0.0),
            (3.0, 10.5),
            (10.0, 10.5),
            (7.0, 0.0),
        ]
        insert_mesh = _make_prism_mesh(insert_pts, y_half=1.75)
        shank_pts = [
            (2.5, 4.0),
            (2.5, 20.0),
            (35.0, 20.0),
            (35.0, 4.0),
        ]
        shank_mesh = _make_prism_mesh(shank_pts, y_half=6.0)
        return insert_mesh, shank_mesh

    elif shape == "V":
        # VNMG 35-degree diamond profiling insert
        insert_pts = [
            (0.0, 0.0),
            (2.2, 12.0),
            (8.5, 12.0),
            (6.3, 0.0),
        ]
        insert_mesh = _make_prism_mesh(insert_pts, y_half=1.75)
        shank_pts = [
            (2.5, 4.0),
            (2.5, 20.0),
            (35.0, 20.0),
            (35.0, 4.0),
        ]
        shank_mesh = _make_prism_mesh(shank_pts, y_half=6.0)
        return insert_mesh, shank_mesh

    else:
        # Default: CNMG / WNMG 80-degree diamond turning insert
        insert_pts = [
            (0.0, 0.0),
            (4.0, 9.0),
            (12.0, 9.0),
            (8.0, 0.0),
        ]
        insert_mesh = _make_prism_mesh(insert_pts, y_half=1.75)
        shank_pts = [
            (2.5, 4.0),
            (2.5, 20.0),
            (35.0, 20.0),
            (35.0, 4.0),
        ]
        shank_mesh = _make_prism_mesh(shank_pts, y_half=6.0)
        return insert_mesh, shank_mesh


def build_simulation_trajectory(
    project: LatheProject,
    op_id: str | None = None,
    step_linear: float = 0.25,
    step_rapid: float = 0.8,
) -> list[SimFrame]:
    """Generates an interpolated list of simulation frames across the toolpath.
    
    If op_id is specified, only that operation is simulated; otherwise all enabled operations
    are serialized into one cohesive machining simulation.
    """
    ops = [
        op for op in project.operations
        if op.enabled and (op_id is None or op.op_id == op_id)
    ]
    if not ops:
        return []

    st = project.stock
    cur_z = st.z_start_mm + 2.0
    cur_x = st.od_radius + 2.0

    frames: list[SimFrame] = []

    for op in ops:
        tool = project.tools.get(op.tool_id)
        tool_name = tool.name if tool else f"T{op.tool_id}"
        feed_val = op.feed_mm_rev if op.feed_mm_rev > 0 else 0.2

        for cmd in op.preview_commands:
            if cmd.mode == "COMMENT":
                continue

            target_z = cmd.z if cmd.z is not None else cur_z
            target_x = cmd.x if cmd.x is not None else cur_x

            if cmd.mode in ("G0", "G1", "G33", "G76", "G41", "G42", "G40"):
                dist = math.hypot(target_z - cur_z, target_x - cur_x)
                if dist < 1e-4:
                    continue
                step_size = step_rapid if cmd.mode == "G0" else step_linear
                n_steps = max(1, int(math.ceil(dist / step_size)))
                for s in range(1, n_steps + 1):
                    t = s / n_steps
                    fz = cur_z + t * (target_z - cur_z)
                    fx = cur_x + t * (target_x - cur_x)
                    frames.append(SimFrame(
                        z=round(fz, 4),
                        x=round(fx, 4),
                        mode=cmd.mode,
                        tool_id=op.tool_id,
                        tool_name=tool_name,
                        op_name=op.name,
                        feed=feed_val,
                    ))
                cur_z, cur_x = target_z, target_x

            elif cmd.mode in ("G2", "G3") and cmd.i is not None and cmd.k is not None:
                center = (cur_z + cmd.k, cur_x + cmd.i)
                pts = discretize_arc((cur_z, cur_x), (target_z, target_x), center, mode=cmd.mode)
                for pz, px in pts[1:]:
                    frames.append(SimFrame(
                        z=round(pz, 4),
                        x=round(px, 4),
                        mode=cmd.mode,
                        tool_id=op.tool_id,
                        tool_name=tool_name,
                        op_name=op.name,
                        feed=feed_val,
                    ))
                cur_z, cur_x = target_z, target_x

            elif cmd.mode in ("G83", "G73"):
                r_plane = cmd.raw_params.get("r_plane", 1.0) if cmd.raw_params else 1.0
                dist = abs(target_z - r_plane)
                n_steps = max(1, int(math.ceil(dist / step_linear)))
                for s in range(1, n_steps + 1):
                    t = s / n_steps
                    fz = r_plane + t * (target_z - r_plane)
                    frames.append(SimFrame(
                        z=round(fz, 4),
                        x=0.0,
                        mode="G1",
                        tool_id=op.tool_id,
                        tool_name=tool_name,
                        op_name=op.name,
                        feed=feed_val,
                    ))
                cur_z, cur_x = target_z, 0.0

    return frames
