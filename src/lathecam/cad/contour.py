from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence
import shapely.geometry
import shapely.ops

from lathecam.cad.geometry import Point2D, resample_polyline


@dataclass
class Contour:
    """Represents a continuous 2D contour in the lathe (Z_axial, X_radius) coordinate system.
    
    Coordinates are in millimeters:
    - Z = 0.0 is the part front face (or target reference face)
    - Z < 0.0 extends toward the chuck
    - X >= 0.0 is the radial dimension
    """
    points: list[Point2D]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError(f"Contour must contain at least 2 points, got {len(self.points)}")

    @property
    def z_values(self) -> list[float]:
        return [p[0] for p in self.points]

    @property
    def x_values(self) -> list[float]:
        return [p[1] for p in self.points]

    @property
    def z_min(self) -> float:
        return min(self.z_values)

    @property
    def z_max(self) -> float:
        return max(self.z_values)

    @property
    def x_min(self) -> float:
        return min(self.x_values)

    @property
    def x_max(self) -> float:
        return max(self.x_values)

    @property
    def length(self) -> float:
        total = 0.0
        for (z1, x1), (z2, x2) in zip(self.points[:-1], self.points[1:]):
            total += math.hypot(z2 - z1, x2 - x1)
        return total

    @property
    def is_closed(self) -> bool:
        first = self.points[0]
        last = self.points[-1]
        return math.hypot(first[0] - last[0], first[1] - last[1]) < 1e-4

    def recenter_front_face(self, z_target: float = 0.0) -> Contour:
        """Shifts all Z coordinates so that the front face (maximum Z) aligns with z_target."""
        current_max_z = self.z_max
        shift = z_target - current_max_z
        shifted_points = [(z + shift, x) for z, x in self.points]
        return Contour(shifted_points)

    def resample(self, step_mm: float = 0.2) -> Contour:
        """Resamples the contour points so adjacent vertices are at most step_mm apart."""
        return Contour(resample_polyline(self.points, step_mm=step_mm))

    def orient_front_to_rear(self) -> Contour:
        """Ensures the contour vertices run from front (+Z) to rear (-Z)."""
        if self.points[0][0] < self.points[-1][0]:
            return Contour(list(reversed(self.points)))
        return Contour(list(self.points))

    def to_shapely_polygon(self, z_min_bound: float | None = None) -> shapely.geometry.Polygon:
        """Converts contour into a closed polygon bounded by X=0 (the spindle centerline)."""
        pts = self.orient_front_to_rear().points
        first_z, first_x = pts[0]
        last_z, last_x = pts[-1]
        z_end = min(last_z, z_min_bound) if z_min_bound is not None else last_z

        poly_coords: list[Point2D] = [(first_z, 0.0)]
        if abs(first_x) > 1e-6:
            poly_coords.append((first_z, first_x))
        poly_coords.extend(pts)
        if abs(last_z - z_end) > 1e-6:
            poly_coords.append((z_end, last_x))
        poly_coords.append((z_end, 0.0))
        poly_coords.append((first_z, 0.0))

        poly = shapely.geometry.Polygon(poly_coords)
        if not poly.is_valid:
            poly = shapely.ops.unary_union(poly)
        return poly


def chain_segments(
    segments: Sequence[Sequence[Point2D]],
    tolerance_mm: float = 0.02,
) -> list[list[Point2D]]:
    """Chains unordered and potentially flipped 2D segments into continuous polyline chains.
    
    Each segment is a sequence of Point2D [(z0, x0), (z1, x1), ...].
    Segments whose endpoints are within tolerance_mm are connected.
    """
    if not segments:
        return []

    # Clean and filter segments with negligible length
    valid_segs: list[list[Point2D]] = []
    for s in segments:
        s_list = list(s)
        if len(s_list) >= 2:
            seg_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(s_list[:-1], s_list[1:]))
            if seg_len > 1e-4:
                valid_segs.append(s_list)

    if not valid_segs:
        return []

    chains: list[list[Point2D]] = []
    remaining = list(valid_segs)

    while remaining:
        current_chain = list(remaining.pop(0))
        extended = True

        while extended:
            extended = False
            head = current_chain[0]
            tail = current_chain[-1]

            best_match_idx = -1
            best_match_action = None
            min_dist = tolerance_mm

            for idx, candidate in enumerate(remaining):
                c_start = candidate[0]
                c_end = candidate[-1]

                # Match at tail of current_chain
                d_tail_start = math.hypot(tail[0] - c_start[0], tail[1] - c_start[1])
                if d_tail_start < min_dist:
                    min_dist = d_tail_start
                    best_match_idx = idx
                    best_match_action = "append"

                d_tail_end = math.hypot(tail[0] - c_end[0], tail[1] - c_end[1])
                if d_tail_end < min_dist:
                    min_dist = d_tail_end
                    best_match_idx = idx
                    best_match_action = "append_reversed"

                # Match at head of current_chain
                d_head_end = math.hypot(head[0] - c_end[0], head[1] - c_end[1])
                if d_head_end < min_dist:
                    min_dist = d_head_end
                    best_match_idx = idx
                    best_match_action = "prepend"

                d_head_start = math.hypot(head[0] - c_start[0], head[1] - c_start[1])
                if d_head_start < min_dist:
                    min_dist = d_head_start
                    best_match_idx = idx
                    best_match_action = "prepend_reversed"

            if best_match_idx >= 0 and best_match_action is not None:
                matched_seg = remaining.pop(best_match_idx)
                if best_match_action == "append":
                    current_chain.extend(matched_seg[1:])
                elif best_match_action == "append_reversed":
                    current_chain.extend(reversed(matched_seg[:-1]))
                elif best_match_action == "prepend":
                    current_chain = matched_seg[:-1] + current_chain
                elif best_match_action == "prepend_reversed":
                    current_chain = list(reversed(matched_seg[1:])) + current_chain
                extended = True

        chains.append(current_chain)

    return chains


def extract_upper_silhouette(
    chains: Sequence[Sequence[Point2D]],
    sample_step_mm: float = 0.25,
) -> Contour:
    """Takes chained curves and extracts the outermost upper silhouette (X >= 0) as a single Contour."""
    # Find points with X >= 0
    all_lines: list[shapely.geometry.LineString] = []
    for chain in chains:
        pts = [(p[0], max(0.0, abs(p[1]))) for p in chain]
        if len(pts) >= 2:
            try:
                ls = shapely.geometry.LineString(pts)
                if ls.length > 1e-4:
                    all_lines.append(ls)
            except Exception:
                pass

    if not all_lines:
        raise ValueError("No valid curve geometry found to extract upper silhouette")

    merged_geom = shapely.ops.unary_union(all_lines)
    min_z, min_x, max_z, max_x = merged_geom.bounds

    z_samples = [max_z]
    curr_z = max_z - sample_step_mm
    while curr_z > min_z:
        z_samples.append(curr_z)
        curr_z -= sample_step_mm
    z_samples.append(min_z)

    silhouette_pts: list[Point2D] = []
    for z in z_samples:
        ray = shapely.geometry.LineString([(z, 0.0), (z, max_x + 10.0)])
        inter = ray.intersection(merged_geom)
        if inter.is_empty:
            continue
        xs: list[float] = []
        if isinstance(inter, shapely.geometry.Point):
            xs.append(inter.y)
        elif isinstance(inter, shapely.geometry.MultiPoint):
            xs.extend(p.y for p in inter.geoms)
        elif isinstance(inter, shapely.geometry.LineString):
            xs.extend(p[1] for p in inter.coords)
        elif isinstance(inter, shapely.geometry.MultiLineString):
            for ls in inter.geoms:
                xs.extend(p[1] for p in ls.coords)
        elif isinstance(inter, shapely.geometry.GeometryCollection):
            for g in inter.geoms:
                if isinstance(g, shapely.geometry.Point):
                    xs.append(g.y)
                elif isinstance(g, shapely.geometry.LineString):
                    xs.extend(p[1] for p in g.coords)

        if xs:
            silhouette_pts.append((float(z), float(max(xs))))

    if len(silhouette_pts) < 2:
        # Fallback: flatten the longest chain
        longest = max(chains, key=len)
        silhouette_pts = [(p[0], max(0.0, abs(p[1]))) for p in longest]

    return Contour(silhouette_pts).recenter_front_face(0.0).orient_front_to_rear()
