from __future__ import annotations

import math
from typing import Sequence
import numpy as np
import shapely.geometry
import shapely.ops

from lathecam.cad.geometry import Point2D
from lathecam.cam.tools import LatheTool


def profile_to_polygon(
    profile_pts: Sequence[Point2D],
    z_min: float | None = None,
    z_max: float | None = None,
) -> shapely.geometry.Polygon:
    """Converts an upper-half (X >= 0) turning profile into a closed 2D polygon in (Z, X) space.
    
    The polygon is closed along the centerline X = 0.
    """
    if len(profile_pts) < 2:
        raise ValueError("Profile must have at least 2 points")

    pts = list(profile_pts)
    # If the profile is already a closed loop (e.g. hollow tube cross-section)
    if len(pts) >= 4 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-4:
        poly = shapely.geometry.Polygon(pts)
        if not poly.is_valid:
            poly = shapely.ops.unary_union(poly)
        return poly

    # Ensure points are ordered from front (max Z) to rear (min Z)
    if pts[0][0] < pts[-1][0]:
        pts.reverse()

    first_z, first_x = pts[0]
    last_z, last_x = pts[-1]

    z_start = first_z if z_max is None else max(first_z, z_max)
    z_end = last_z if z_min is None else min(last_z, z_min)

    poly_coords: list[Point2D] = []
    # Front vertical line from X=0 to first point
    poly_coords.append((z_start, 0.0))
    if abs(first_z - z_start) > 1e-6 or first_x > 0:
        poly_coords.append((z_start, first_x))

    poly_coords.extend(pts)

    # Rear vertical line to X=0
    if abs(last_z - z_end) > 1e-6:
        poly_coords.append((z_end, last_x))
    poly_coords.append((z_end, 0.0))
    poly_coords.append((z_start, 0.0))

    poly = shapely.geometry.Polygon(poly_coords)
    if not poly.is_valid:
        poly = shapely.ops.unary_union(poly)
    return poly


def compute_shadowed_polygon(
    profile_pts: Sequence[Point2D],
    tool: LatheTool,
    z_min_bound: float | None = None,
    z_max_bound: float | None = None,
) -> shapely.geometry.Polygon:
    """Computes the reachable silhouette of a turning part polygon using tool clearance and lead angles.
    
    Any steep drop-off or undercut exceeding the tool's trailing flank clearance angle is bridged
    by unioning a shadow wedge with the part polygon.
    """
    pts = list(profile_pts)
    if len(pts) < 2:
        raise ValueError("Profile must have at least 2 points")

    if pts[0][0] < pts[-1][0]:
        pts.reverse()

    base_poly = profile_to_polygon(pts, z_min=z_min_bound, z_max=z_max_bound)

    min_z = min(p[0] for p in pts) if z_min_bound is None else z_min_bound
    max_z = max(p[0] for p in pts) if z_max_bound is None else z_max_bound
    max_x = max(p[1] for p in pts)

    clearance_rad = math.radians(max(0.5, tool.clearance_angle_deg))
    clearance_slope = math.tan(clearance_rad)  # Drop in X per mm of movement toward -Z

    shadow_wedges: list[shapely.geometry.Polygon] = []

    # 1. Forward Trailing Flank Shadow (from +Z to -Z, standard OD turning)
    for i in range(len(pts) - 1):
        z0, x0 = pts[i]
        z1, x1 = pts[i + 1]

        dz = z1 - z0  # Non-positive when moving toward -Z
        dx = x1 - x0

        is_vertical_drop = abs(dz) <= 1e-6 and dx < -1e-6
        is_steep_drop = dz < -1e-6 and dx < 0 and (-dx / -dz) > clearance_slope

        if is_vertical_drop or is_steep_drop:
            # Project a straight clearance ray from (z0, x0) at slope: x(z) = x0 - clearance_slope * (z0 - z)
            if clearance_slope > 1e-9:
                z_zero = z0 - (x0 / clearance_slope)
                z_end_ray = max(min_z, z_zero)
            else:
                z_end_ray = min_z
            x_end_ray = max(0.0, x0 - clearance_slope * (z0 - z_end_ray))

            wedge_coords = [
                (z0, x0),
                (z_end_ray, x_end_ray),
                (z_end_ray, 0.0),
                (z0, 0.0),
                (z0, x0),
            ]
            try:
                wedge_poly = shapely.geometry.Polygon(wedge_coords)
                if wedge_poly.is_valid and not wedge_poly.is_empty:
                    shadow_wedges.append(wedge_poly)
            except Exception:
                pass

    # 2. Lead / Approach Angle Shadow on rising shoulders (when lead_angle_deg < 90 deg)
    lead_deg = tool.lead_angle_deg
    if 1.0 < lead_deg < 89.9:
        max_rise_slope = math.tan(math.radians(lead_deg))  # Max dX / |-dZ| climb slope
        for i in range(len(pts) - 1):
            z0, x0 = pts[i]
            z1, x1 = pts[i + 1]
            dz = z1 - z0
            dx = x1 - x0
            is_vertical_rise = abs(dz) <= 1e-6 and dx > 1e-6
            is_steep_rise = dz < -1e-6 and dx > 0 and (dx / -dz) > max_rise_slope
            if is_vertical_rise or is_steep_rise:
                z_foot = min(max_z, z1 + (x1 / max_rise_slope))
                wedge_coords = [
                    (z1, x1),
                    (z_foot, 0.0),
                    (z1, 0.0),
                    (z1, x1),
                ]
                try:
                    wedge_poly = shapely.geometry.Polygon(wedge_coords)
                    if wedge_poly.is_valid and not wedge_poly.is_empty:
                        shadow_wedges.append(wedge_poly)
                except Exception:
                    pass

    if not shadow_wedges:
        return base_poly

    combined_shadow = shapely.ops.unary_union(shadow_wedges)
    # Clip shadow within bounding box
    bbox = shapely.geometry.box(min_z, 0.0, max_z, max_x + 10.0)
    shadowed_poly = shapely.ops.unary_union([base_poly, combined_shadow.intersection(bbox)])
    return shadowed_poly


def extract_upper_profile(
    polygon: shapely.geometry.Polygon | shapely.geometry.MultiPolygon,
    sample_step_mm: float | None = None,
) -> list[Point2D]:
    """Extracts the exact sequence of (Z, X_radius) vertices along the top silhouette of a polygon."""
    if polygon.is_empty:
        return []

    if isinstance(polygon, shapely.geometry.MultiPolygon):
        poly = max(polygon.geoms, key=lambda g: g.area)
    else:
        poly = polygon

    oriented = shapely.geometry.polygon.orient(poly, sign=1.0)
    ring = list(oriented.exterior.coords)[:-1]
    if len(ring) < 3:
        return []

    min_z, _, max_z, _ = oriented.bounds

    # Find the bottom-right corner near (max_z, 0.0) and bottom-left corner near (min_z, 0.0)
    idx_start = min(
        range(len(ring)),
        key=lambda k: math.hypot(ring[k][0] - max_z, ring[k][1] - 0.0),
    )
    rotated = ring[idx_start:] + ring[:idx_start]
    idx_end = min(
        range(len(rotated)),
        key=lambda k: math.hypot(rotated[k][0] - min_z, rotated[k][1] - 0.0),
    )

    upper_chain = rotated[: idx_end + 1]
    profile: list[Point2D] = []
    for z, x in upper_chain:
        if x <= 1e-5:
            continue
        pt = (float(z), float(x))
        if not profile or math.hypot(pt[0] - profile[-1][0], pt[1] - profile[-1][1]) > 1e-6:
            profile.append(pt)

    return profile


def compute_shadowed_profile(
    profile_pts: Sequence[Point2D],
    tool: LatheTool,
    sample_step_mm: float = 0.5,
    z_min_bound: float | None = None,
    z_max_bound: float | None = None,
) -> list[Point2D]:
    """High-level function: Returns the shadowed profile (Z, X) as an exact vertex sequence."""
    shadowed_poly = compute_shadowed_polygon(
        profile_pts,
        tool,
        z_min_bound=z_min_bound,
        z_max_bound=z_max_bound,
    )
    return extract_upper_profile(shadowed_poly, sample_step_mm=sample_step_mm)

