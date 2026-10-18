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
            # We project a ray from (z0, x0) at slope: x(z) = x0 - clearance_slope * (z0 - z)
            ray_pts = [(z0, x0)]
            curr_z = z0
            while curr_z > min_z:
                curr_z = max(min_z, curr_z - 0.25)
                curr_x = x0 - clearance_slope * (z0 - curr_z)
                ray_pts.append((curr_z, max(0.0, curr_x)))

                # Complete shadow wedge polygon down to X=0
                last_ray_z, last_ray_x = ray_pts[-1]
                wedge_coords = list(ray_pts)
                wedge_coords.append((last_ray_z, 0.0))
                wedge_coords.append((z0, 0.0))
                wedge_coords.append((z0, x0))

                try:
                    wedge_poly = shapely.geometry.Polygon(wedge_coords)
                    if wedge_poly.is_valid and not wedge_poly.is_empty:
                        shadow_wedges.append(wedge_poly)
                except Exception:
                    pass

    # 2. Reverse / Overhang Shadow (Lead Angle Check)
    # Lead angle relative to cut direction
    lead_deg = tool.lead_angle_deg
    if lead_deg > 90.0:
        back_relief_deg = lead_deg - 90.0
        back_relief_rad = math.radians(back_relief_deg)
        lead_slope = math.tan(back_relief_rad)

        for i in range(len(pts) - 1, 0, -1):
            z0, x0 = pts[i]      # Rearward point
            z1, x1 = pts[i - 1]  # Forward point

            dz = z1 - z0  # Positive (towards +Z)
            dx = x1 - x0

            # If profile drops going from rear to front (re-entrant wall):
            if dz > 1e-6 and dx < -1e-6:
                ray_pts = [(z0, x0)]
                curr_z = z0
                while curr_z < max_z:
                    curr_z = min(max_z, curr_z + 0.5)
                    curr_x = x0 - lead_slope * (curr_z - z0)
                    ray_pts.append((curr_z, max(0.0, curr_x)))

                last_ray_z, last_ray_x = ray_pts[-1]
                wedge_coords = list(ray_pts)
                wedge_coords.append((last_ray_z, 0.0))
                wedge_coords.append((z0, 0.0))
                wedge_coords.append((z0, x0))

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
    sample_step_mm: float = 0.5,
) -> list[Point2D]:
    """Extracts a smooth sequence of (Z, X_radius) points along the top silhouette of a polygon."""
    min_z, min_x, max_z, max_x = polygon.bounds

    z_vals = np.arange(max_z, min_z - 1e-6, -sample_step_mm)
    if len(z_vals) == 0 or z_vals[-1] > min_z + 1e-6:
        z_vals = np.append(z_vals, min_z)

    profile: list[Point2D] = []
    for z in z_vals:
        # Cast a vertical ray at Z = z from X=0 to max_x + 1
        ray = shapely.geometry.LineString([(z, 0.0), (z, max_x + 5.0)])
        inter = ray.intersection(polygon)
        if inter.is_empty:
            continue
        if isinstance(inter, shapely.geometry.LineString):
            top_x = max(p[1] for p in inter.coords)
            profile.append((float(z), float(top_x)))
        elif isinstance(inter, shapely.geometry.MultiLineString):
            top_x = max(max(p[1] for p in ls.coords) for ls in inter.geoms)
            profile.append((float(z), float(top_x)))
        elif isinstance(inter, shapely.geometry.Point):
            profile.append((float(z), float(inter.y)))
        elif isinstance(inter, shapely.geometry.GeometryCollection):
            xs = [g.y for g in inter.geoms if isinstance(g, shapely.geometry.Point)]
            for g in inter.geoms:
                if isinstance(g, shapely.geometry.LineString):
                    xs.extend([p[1] for p in g.coords])
            if xs:
                profile.append((float(z), float(max(xs))))

    return profile


def compute_shadowed_profile(
    profile_pts: Sequence[Point2D],
    tool: LatheTool,
    sample_step_mm: float = 0.5,
    z_min_bound: float | None = None,
    z_max_bound: float | None = None,
) -> list[Point2D]:
    """High-level function: Returns the shadowed profile (Z, X) as a discrete point sequence."""
    shadowed_poly = compute_shadowed_polygon(
        profile_pts,
        tool,
        z_min_bound=z_min_bound,
        z_max_bound=z_max_bound,
    )
    return extract_upper_profile(shadowed_poly, sample_step_mm=sample_step_mm)
