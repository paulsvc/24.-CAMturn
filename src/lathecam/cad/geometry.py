from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence
import numpy as np

from lathecam.cam.commands import MotionCmd

Point2D = tuple[float, float]  # (z, x_radius)


@dataclass
class LineSegment:
    start: Point2D
    end: Point2D

    def to_motion_cmd(self, feed: float | None = None) -> MotionCmd:
        return MotionCmd.linear(x=self.end[1], z=self.end[0], f=feed)


@dataclass
class ArcSegment:
    mode: str  # 'G2' (clockwise) or 'G3' (counter-clockwise)
    start: Point2D
    end: Point2D
    center: Point2D
    radius: float

    @property
    def i(self) -> float:
        """Incremental X center offset from arc start (strictly radius mm)."""
        return self.center[1] - self.start[1]

    @property
    def k(self) -> float:
        """Incremental Z center offset from arc start mm."""
        return self.center[0] - self.start[0]

    def to_motion_cmd(self, feed: float | None = None) -> MotionCmd:
        return MotionCmd.arc(
            mode=self.mode,
            x=self.end[1],
            z=self.end[0],
            i=self.i,
            k=self.k,
            f=feed,
        )


def point_line_distance(pt: Point2D, line_start: Point2D, line_end: Point2D) -> float:
    """Computes perpendicular distance from pt to line segment (line_start, line_end)."""
    z0, x0 = pt
    z1, x1 = line_start
    z2, x2 = line_end

    dx = x2 - x1
    dz = z2 - z1
    seg_len_sq = dz * dz + dx * dx
    if seg_len_sq < 1e-12:
        return math.hypot(z0 - z1, x0 - x1)

    t = max(0.0, min(1.0, ((z0 - z1) * dz + (x0 - x1) * dx) / seg_len_sq))
    proj_z = z1 + t * dz
    proj_x = x1 + t * dx
    return math.hypot(z0 - proj_z, x0 - proj_x)


def fit_circle_kasa(points: Sequence[Point2D]) -> tuple[Point2D, float, float] | None:
    """Fits a circle to 2D points in (Z, X) plane using Kåsa's algebraic least-squares method.
    
    Returns:
        ((z_center, x_center), radius, max_radial_error) or None if collinear / singular.
    """
    if len(points) < 3:
        return None

    pts = np.array(points, dtype=np.float64)
    z = pts[:, 0]
    x = pts[:, 1]

    # Model: (z - z_c)^2 + (x - x_c)^2 = R^2
    # -> 2*z*z_c + 2*x*x_c + c = z^2 + x^2
    A = np.column_stack((2 * z, 2 * x, np.ones_like(z)))
    b = z**2 + x**2

    try:
        sol, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None

    if rank < 3:
        return None

    zc, xc, c = sol
    r_sq = c + zc**2 + xc**2
    if r_sq <= 0:
        return None

    radius = math.sqrt(r_sq)
    dists = np.hypot(z - zc, x - xc)
    max_error = float(np.max(np.abs(dists - radius)))

    return ((float(zc), float(xc)), radius, max_error)


def determine_arc_mode(start: Point2D, mid: Point2D, end: Point2D, center: Point2D) -> str:
    """Determines G2 (CW) or G3 (CCW) chirality in LinuxCNC G18 (ZX plane).
    
    In G18 (Z=horizontal, X=vertical):
    Cross product of (P_start -> P_center) with (P_center -> P_end) or
    (P_start - P_center) x (P_end - P_center).
    Let u = Z, v = X:
    cross = (z1 - zc)*(x2 - xc) - (x1 - xc)*(z2 - zc)
    cross < 0 is CW ('G2')
    cross > 0 is CCW ('G3')
    """
    zc, xc = center
    z1, x1 = start
    zm, xm = mid
    z2, x2 = end

    # Test rotation across intermediate point to avoid >180 deg ambiguity
    cross1 = (z1 - zc) * (xm - xc) - (x1 - xc) * (zm - zc)
    if abs(cross1) > 1e-9:
        return "G2" if cross1 < 0 else "G3"

    cross2 = (zm - zc) * (x2 - xc) - (xm - xc) * (z2 - zc)
    return "G2" if cross2 < 0 else "G3"


def _project_center_to_bisector(
    start: Point2D,
    end: Point2D,
    raw_center: Point2D,
    radius: float,
) -> tuple[Point2D, float]:
    """Projects a circle center onto the exact perpendicular bisector of (start, end)
    so that dist(start, center) == dist(end, center) to machine precision.
    """
    z1, x1 = start
    z2, x2 = end
    dz = z2 - z1
    dx = x2 - x1
    chord = math.hypot(dz, dx)
    if chord < 1e-9:
        return raw_center, radius

    r = max(radius, chord * 0.5 + 1e-6)
    h = math.sqrt(max(0.0, r * r - (chord * 0.5) ** 2))
    mz = 0.5 * (z1 + z2)
    mx = 0.5 * (x1 + x2)
    nz = -dx / chord
    nx = dz / chord

    c1 = (mz + h * nz, mx + h * nx)
    c2 = (mz - h * nz, mx - h * nx)
    d1 = math.hypot(c1[0] - raw_center[0], c1[1] - raw_center[1])
    d2 = math.hypot(c2[0] - raw_center[0], c2[1] - raw_center[1])
    best_c = c1 if d1 <= d2 else c2
    exact_r = math.hypot(z1 - best_c[0], x1 - best_c[1])
    return best_c, exact_r


def _simplify_collinear(points: Sequence[Point2D], tol: float = 1e-4) -> list[Point2D]:
    """Merges consecutive collinear vertices within tol while preserving corners and curve points."""
    if len(points) <= 2:
        return list(points)
    out: list[Point2D] = [points[0]]
    for pt in points[1:]:
        if math.hypot(pt[0] - out[-1][0], pt[1] - out[-1][1]) > 1e-6:
            out.append(pt)
    if len(out) <= 2:
        return out

    simplified: list[Point2D] = [out[0]]
    i = 0
    n = len(out)
    while i < n - 1:
        # Check if out[i+1] is strictly collinear between out[i] and out[i+2]
        j = i + 1
        while j + 1 < n:
            dev = max(point_line_distance(out[k], out[i], out[j + 1]) for k in range(i + 1, j + 1))
            if dev <= tol:
                j += 1
            else:
                break
        simplified.append(out[j])
        i = j
    return simplified


def fit_arcs_to_polyline(
    points: Sequence[Point2D],
    chordal_tolerance_mm: float = 0.005,
    min_arc_points: int = 4,
    max_arc_radius_mm: float = 100.0,
) -> list[LineSegment | ArcSegment]:
    """Reconstructs continuous G1 line segments and G2/G3 circular arcs from a discrete polyline.
    
    Enforces:
    - Collinear segments are simplified first so straight lines are never merged with corner points.
    - Uniform chord step length and consistent curvature direction across all points in an arc.
    - Exact perpendicular bisector center projection so dist(start, center) == dist(end, center).
    """
    pts = _simplify_collinear(points, tol=min(1e-4, chordal_tolerance_mm * 0.1))
    if len(pts) < 2:
        return []
    if len(pts) == 2:
        return [LineSegment(pts[0], pts[1])]

    result: list[LineSegment | ArcSegment] = []
    i = 0
    n = len(pts)

    while i < n - 1:
        best_arc: ArcSegment | None = None
        best_arc_len = 0

        for j in range(i + min_arc_points, n + 1):
            sub_pts = pts[i:j]

            # 1. Check chord lengths are reasonably uniform and not long straight lines
            chords = [
                math.hypot(sub_pts[k + 1][0] - sub_pts[k][0], sub_pts[k + 1][1] - sub_pts[k][1])
                for k in range(len(sub_pts) - 1)
            ]
            max_chord = max(chords)
            min_chord = max(1e-6, min(chords))
            if max_chord > 3.5 or (max_chord / min_chord) > 3.5:
                break

            # 2. Check consistent turning direction (no inflection points or straight lines)
            cross_signs: list[int] = []
            valid_turn = True
            for k in range(len(sub_pts) - 2):
                dz1 = sub_pts[k + 1][0] - sub_pts[k][0]
                dx1 = sub_pts[k + 1][1] - sub_pts[k][1]
                dz2 = sub_pts[k + 2][0] - sub_pts[k + 1][0]
                dx2 = sub_pts[k + 2][1] - sub_pts[k + 1][1]
                cr = dz1 * dx2 - dx1 * dz2
                if abs(cr) < 1e-6:
                    valid_turn = False
                    break
                cross_signs.append(1 if cr > 0 else -1)
            if not valid_turn or len(set(cross_signs)) > 1:
                break

            # 3. Check sagitta (bulge height) is meaningfully curved
            max_line_dev = max(point_line_distance(pt, sub_pts[0], sub_pts[-1]) for pt in sub_pts)
            if max_line_dev <= max(0.01, chordal_tolerance_mm * 2.5):
                continue

            # 4. Fit circle via Kåsa and project center onto exact perpendicular bisector
            fit = fit_circle_kasa(sub_pts)
            if fit is None:
                break

            raw_center, raw_radius, _ = fit
            if raw_radius < 0.08 or raw_radius > max_arc_radius_mm:
                break

            center, radius = _project_center_to_bisector(sub_pts[0], sub_pts[-1], raw_center, raw_radius)
            max_dev = max(
                abs(math.hypot(pt[0] - center[0], pt[1] - center[1]) - radius)
                for pt in sub_pts
            )
            if max_dev > chordal_tolerance_mm:
                break

            # 5. Check that arc sweep angle is <= 120 degrees
            zc, xc = center
            start_vec = (sub_pts[0][0] - zc, sub_pts[0][1] - xc)
            end_vec = (sub_pts[-1][0] - zc, sub_pts[-1][1] - xc)
            dot = start_vec[0] * end_vec[0] + start_vec[1] * end_vec[1]
            cos_theta = max(-1.0, min(1.0, dot / (radius * radius)))
            if cos_theta < -0.25:
                break

            mid_idx = len(sub_pts) // 2
            mode = determine_arc_mode(sub_pts[0], sub_pts[mid_idx], sub_pts[-1], center)
            best_arc = ArcSegment(
                mode=mode,
                start=sub_pts[0],
                end=sub_pts[-1],
                center=center,
                radius=radius,
            )
            best_arc_len = j - i

        if best_arc is not None and best_arc_len >= min_arc_points:
            result.append(best_arc)
            i += best_arc_len - 1
        else:
            # Extend straight line segment as far as collinear within tolerance
            j = i + 1
            while j < n:
                candidate_pts = pts[i : j + 1]
                max_dev = max(
                    point_line_distance(pt, candidate_pts[0], candidate_pts[-1])
                    for pt in candidate_pts
                )
                if max_dev > chordal_tolerance_mm:
                    break
                j += 1
            line_end_idx = max(i + 1, j - 1)
            result.append(LineSegment(pts[i], pts[line_end_idx]))
            i = line_end_idx

    return result



def resample_polyline(points: Sequence[Point2D], step_mm: float = 0.5) -> list[Point2D]:
    """Resamples a polyline so adjacent vertices are spaced no further than step_mm."""
    if len(points) < 2:
        return list(points)

    resampled: list[Point2D] = [points[0]]
    for (z1, x1), (z2, x2) in zip(points[:-1], points[1:]):
        dist = math.hypot(z2 - z1, x2 - x1)
        if dist <= 1e-9:
            continue
        num_steps = max(1, int(math.ceil(dist / step_mm)))
        for k in range(1, num_steps + 1):
            t = k / num_steps
            resampled.append((z1 + t * (z2 - z1), x1 + t * (x2 - x1)))

    return resampled
