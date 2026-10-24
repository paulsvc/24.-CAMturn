"""3D Mesh Generator for LatheCAM Workpiece and Stock.

Converts 2D meridian profile points into 3D revolved triangle meshes (vertices, normals, indices)
with optional 3/4 cutaway wedge for inspecting internal drilled holes and profiles in WebGL/Three.js.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np


def generate_revolved_mesh(
    profile_pts: list[tuple[float, float]],
    num_slices: int = 48,
    cutaway: bool = True,
    cutaway_angle_deg: float = 90.0,
) -> dict[str, Any]:
    """Revolves a 2D meridian contour (z, x_radius) around the Z axis.
    
    Returns a dict compatible with Three.js BufferGeometry:
      - vertices: list[float] (flat [x, y, z, ...])
      - normals: list[float]
      - indices: list[int]
    """
    if not profile_pts or len(profile_pts) < 2:
        return {"vertices": [], "normals": [], "indices": []}

    # Clean profile points: ensure radius >= 0
    clean_pts: list[tuple[float, float]] = []
    for z, x in profile_pts:
        clean_pts.append((float(z), max(0.0, float(x))))

    # Angle range for revolution
    if cutaway:
        # A 270-degree arc leaving a 90-degree quadrant open
        theta_start = math.radians(cutaway_angle_deg)
        theta_end = 2.0 * math.pi
    else:
        theta_start = 0.0
        theta_end = 2.0 * math.pi

    angles = np.linspace(theta_start, theta_end, num_slices, endpoint=cutaway)
    n_angles = len(angles)
    n_pts = len(clean_pts)

    vertices: list[float] = []
    normals: list[float] = []
    indices: list[int] = []

    # 1. Generate grid of vertices on the revolved surface
    # Vertex index mapping: grid[pt_idx, angle_idx] = base_idx
    grid = np.zeros((n_pts, n_angles), dtype=int)
    vert_count = 0

    for i, (z, r) in enumerate(clean_pts):
        for j, th in enumerate(angles):
            # In 3D space: Z is lathe spindle axis, X and Y are cross-section
            # Three.js convention: X is right, Y is up, Z is toward viewer
            # Here: map lathe Z -> 3D X (or Z), lathe X -> Y/Z
            # Let's map Lathe (Z, X_rad, Y_rad) -> 3D (X=Z_lathe, Y=X_rad*cos, Z=X_rad*sin)
            px = z
            py = r * math.cos(th)
            pz = r * math.sin(th)
            vertices.extend([round(px, 4), round(py, 4), round(pz, 4)])

            # Normal approximation for cylinder/revolve
            # Radial outward vector
            norm_r = 1.0 if r > 1e-4 else 0.0
            nx = 0.0
            ny = norm_r * math.cos(th)
            nz = norm_r * math.sin(th)
            normals.extend([round(nx, 4), round(ny, 4), round(nz, 4)])

            grid[i, j] = vert_count
            vert_count += 1

    # Triangulate the curved surface
    for i in range(n_pts - 1):
        for j in range(n_angles - 1):
            p00 = int(grid[i, j])
            p01 = int(grid[i, j + 1])
            p10 = int(grid[i + 1, j])
            p11 = int(grid[i + 1, j + 1])

            # Two triangles per quad
            indices.extend([p00, p10, p01])
            indices.extend([p01, p10, p11])

        if not cutaway:
            # Close revolution seam
            p00 = int(grid[i, n_angles - 1])
            p01 = int(grid[i, 0])
            p10 = int(grid[i + 1, n_angles - 1])
            p11 = int(grid[i + 1, 0])
            indices.extend([p00, p10, p01])
            indices.extend([p01, p10, p11])

    # 2. If cutaway, cap the two cut slice planes so internal profile is solid
    if cutaway:
        # Cut plane 1 at theta_start
        th1 = theta_start
        cos1, sin1 = math.cos(th1), math.sin(th1)
        # Normal to plane 1: pointing clockwise
        n1 = (-sin1, cos1)  # 2D cross-section normal

        plane1_start_idx = vert_count
        for z, r in clean_pts:
            vertices.extend([round(z, 4), round(r * cos1, 4), round(r * sin1, 4)])
            normals.extend([0.0, round(-sin1, 4), round(cos1, 4)])
            vert_count += 1

        # Cut plane 2 at theta_end (2*pi)
        th2 = theta_end
        cos2, sin2 = math.cos(th2), math.sin(th2)
        plane2_start_idx = vert_count
        for z, r in clean_pts:
            vertices.extend([round(z, 4), round(r * cos2, 4), round(r * sin2, 4)])
            normals.extend([0.0, round(sin2, 4), round(-cos2, 4)])
            vert_count += 1

        # Ear-clipping or strip triangulation for the cut planes
        # Since profile is simple polygon along Z, triangulate adjacent segments to centerline
        for i in range(n_pts - 1):
            i0 = plane1_start_idx + i
            i1 = plane1_start_idx + i + 1
            indices.extend([i0, i1, plane1_start_idx])  # Fan triangulation

            j0 = plane2_start_idx + i
            j1 = plane2_start_idx + i + 1
            indices.extend([j0, plane2_start_idx, j1])

    return {
        "vertices": vertices,
        "normals": normals,
        "indices": indices,
    }


def generate_stock_mesh(
    od_mm: float,
    z_start_mm: float,
    z_end_mm: float,
    id_mm: float = 0.0,
    num_slices: int = 36,
) -> dict[str, Any]:
    """Generates a cylindrical 3D stock envelope mesh."""
    r_out = od_mm / 2.0
    r_in = id_mm / 2.0

    profile = [
        (z_start_mm, r_in),
        (z_start_mm, r_out),
        (z_end_mm, r_out),
        (z_end_mm, r_in),
        (z_start_mm, r_in),
    ]

    return generate_revolved_mesh(profile, num_slices=num_slices, cutaway=False)
