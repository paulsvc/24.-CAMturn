from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
import shapely.geometry

from lathecam.cad.geometry import Point2D
from lathecam.models.stock import Stock


@dataclass
class GCodeIssue:
    line_number: int
    code: str
    severity: str  # "ERROR" or "WARNING"
    message: str
    raw_line: str


@dataclass
class BackplotMove:
    line_number: int
    mode: str  # "G0", "G1", "G2", "G3", "G33", "G76", "G83", "G74"
    start: Point2D  # (z, x_radius)
    end: Point2D    # (z, x_radius)
    center: Point2D | None = None
    radius: float | None = None
    sweep_deg: float | None = None
    tool_id: int = 1
    feed: float | None = None


@dataclass
class VerificationReport:
    is_valid: bool
    issues: list[GCodeIssue] = field(default_factory=list)
    moves: list[BackplotMove] = field(default_factory=list)
    total_lines: int = 0
    rapid_count: int = 0
    linear_count: int = 0
    arc_count: int = 0
    cycle_count: int = 0
    max_arc_radius_error_mm: float = 0.0
    max_part_gouge_mm: float = 0.0
    bounding_box: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def summary(self) -> str:
        status = "PASS (VALID)" if self.is_valid else f"FAIL ({self.error_count} errors)"
        lines = [
            f"G-Code Verification: {status}",
            f"  Lines: {self.total_lines} | Moves: G0={self.rapid_count}, G1={self.linear_count}, G2/G3={self.arc_count}, Cycles={self.cycle_count}",
            f"  Max Arc Radius Error: {self.max_arc_radius_error_mm:.5f} mm | Max Part Gouge: {self.max_part_gouge_mm:.4f} mm",
        ]
        for issue in self.issues:
            lines.append(f"  [{issue.severity}] Line {issue.line_number} ({issue.code}): {issue.message} -> `{issue.raw_line}`")
        return "\n".join(lines)


def _sample_arc_points(
    start: Point2D,
    end: Point2D,
    center: Point2D,
    mode: str,
    xz_arc_chirality: bool = False,
    num_samples: int = 16,
) -> tuple[list[Point2D], float]:
    """Samples points along a G18 circular arc and returns (points, sweep_degrees)."""
    z1, x1 = start
    z2, x2 = end
    zc, xc = center
    r = math.hypot(z1 - zc, x1 - xc)
    if r < 1e-9:
        return [start, end], 0.0

    a1 = math.atan2(x1 - xc, z1 - zc)
    a2 = math.atan2(x2 - xc, z2 - zc)

    is_cw_in_zx = (mode in ("G2", "G02")) if not xz_arc_chirality else (mode in ("G3", "G03"))

    if is_cw_in_zx:
        # Clockwise in (Z=right, X=up): angle decreases
        delta = a2 - a1
        while delta > 1e-7:
            delta -= 2.0 * math.pi
        if abs(delta) < 1e-6 and math.hypot(z2 - z1, x2 - x1) > 1e-4:
            delta = -2.0 * math.pi
    else:
        # Counter-clockwise in (Z=right, X=up): angle increases
        delta = a2 - a1
        while delta < -1e-7:
            delta += 2.0 * math.pi
        if abs(delta) < 1e-6 and math.hypot(z2 - z1, x2 - x1) > 1e-4:
            delta = 2.0 * math.pi

    pts: list[Point2D] = []
    for k in range(num_samples + 1):
        theta = a1 + (k / num_samples) * delta
        pts.append((zc + r * math.cos(theta), xc + r * math.sin(theta)))
    return pts, abs(math.degrees(delta))


def verify_gcode(
    gcode_text: str,
    stock: Stock | None = None,
    part_polygon: shapely.geometry.Polygon | None = None,
    is_diameter_mode: bool | None = None,
    max_arc_radius_mm: float = 100.0,
    arc_radius_tol_mm: float = 0.005,
    gouge_tol_mm: float = 0.05,
    finishing_nose_radius_mm: float = 0.4,
) -> VerificationReport:
    """Automatically parses, backplots, and geometrically verifies generated lathe G-code.
    
    Checks:
    1. G18 plane activation and G7/G8 diameter/radius coordinate scaling.
    2. Arc endpoint radius consistency: |hypot(I, K) - hypot(end - center)| <= arc_radius_tol_mm.
    3. Runaway arc radius (> max_arc_radius_mm) and unintended >185 deg loop wraps.
    4. Diagonal rapid (G0) moves inside the stock envelope and rapid collisions with the part.
    5. Cutting move (G1/G2/G3) part gouges against the target part polygon (accounting for TNRC).
    6. Spindle (M3/M03) and Feedrate (F) readiness before cutting moves.
    7. Zero-length moves and redundant duplicate rapids.
    """
    issues: list[GCodeIssue] = []
    moves: list[BackplotMove] = []

    raw_lines = gcode_text.splitlines()
    total_lines = len(raw_lines)

    detected_diameter_mode = True if is_diameter_mode is None else is_diameter_mode
    xz_arc_chirality = False

    for line in raw_lines:
        upper_raw = line.upper()
        if "1:1 RADIUS MODE FOR CARTESIAN BACKPLOTTERS" in upper_raw:
            if is_diameter_mode is None:
                detected_diameter_mode = False
            xz_arc_chirality = True
        clean = re.sub(r"\(.*?\)", "", upper_raw)
        g_tokens = re.findall(r"\bG0*(\d+)\b", clean)
        if "8" in g_tokens and is_diameter_mode is None:
            detected_diameter_mode = False
        elif "7" in g_tokens and is_diameter_mode is None:
            detected_diameter_mode = True

    x_scale = 2.0 if detected_diameter_mode else 1.0

    curr_z: float | None = None
    curr_x: float | None = None  # Always stored in radius mm internally
    active_motion: str = "G0"
    active_tool: int = 1
    active_feed: float | None = None
    spindle_running: bool = False
    plane_g18_set: bool = False

    in_parting_op: bool = False
    in_threading_op: bool = False
    in_drilling_op: bool = False
    in_computer_tnrc: bool = False

    rapid_count = 0
    linear_count = 0
    arc_count = 0
    cycle_count = 0
    max_arc_err = 0.0
    max_gouge = 0.0

    all_z: list[float] = []
    all_x: list[float] = []

    token_re = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")

    for idx, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped == "%":
            continue

        # Check for nested comments, e.g. (foo (bar))
        comment_depth = 0
        has_nested = False
        for ch in stripped:
            if ch == "(":
                if comment_depth > 0:
                    has_nested = True
                comment_depth += 1
            elif ch == ")":
                comment_depth = max(0, comment_depth - 1)
        if has_nested:
            issues.append(GCodeIssue(
                line_number=idx,
                code="NESTED_COMMENT",
                severity="ERROR",
                message="Nested comment found; parenthetical comments cannot contain '(' or ')'",
                raw_line=stripped,
            ))

        # Check comment for operation context
        if stripped.startswith("(") and stripped.endswith(")"):
            upper_c = stripped.upper()
            if "PARTING" in upper_c or "GROOVING" in upper_c:
                in_parting_op = "END" not in upper_c
            elif "THREADING" in upper_c:
                in_threading_op = "END" not in upper_c
            elif "DRILLING" in upper_c:
                in_drilling_op = "END" not in upper_c
            elif "FINISHING PASS" in upper_c:
                if "END" in upper_c:
                    in_computer_tnrc = False
                elif "COMPUTER COMP" in upper_c:
                    in_computer_tnrc = True
            continue

        code_part = re.sub(r"\(.*?\)", "", stripped).strip().upper()
        if not code_part:
            continue

        pairs = token_re.findall(code_part)
        if not pairs:
            continue

        g_codes: list[int] = []
        m_codes: list[int] = []
        words: dict[str, float] = {}

        for letter, val_str in pairs:
            if letter == "G":
                g_codes.append(int(float(val_str)))
            elif letter == "M":
                m_codes.append(int(float(val_str)))
            elif letter == "T":
                t_val = int(float(val_str))
                active_tool = t_val // 100 if t_val >= 100 else t_val
            else:
                words[letter] = float(val_str)

        if 18 in g_codes:
            plane_g18_set = True
        if 3 in m_codes or 4 in m_codes:
            spindle_running = True
        if 5 in m_codes or 30 in m_codes:
            spindle_running = False
        if "F" in words and not any(g in (76, 33) for g in g_codes):
            active_feed = words["F"]

        motion_g = None
        for g in g_codes:
            if g in (0, 1, 2, 3, 33, 74, 76, 83):
                motion_g = f"G{g}"
                if g in (0, 1, 2, 3):
                    active_motion = motion_g

        # Ignore pure setup lines (e.g. G50 S2500, G96, G97, G28, G80)
        if any(g in (28, 50, 80, 96, 97) for g in g_codes) and motion_g is None:
            continue

        has_coords = ("X" in words) or ("Z" in words)
        if not has_coords and motion_g not in ("G76", "G83", "G74"):
            continue

        mode = motion_g if motion_g is not None else active_motion

        target_x = (words["X"] / x_scale) if "X" in words else curr_x
        target_z = words["Z"] if "Z" in words else curr_z

        if target_x is not None:
            all_x.append(target_x)
        if target_z is not None:
            all_z.append(target_z)

        # Canned cycles (G76, G83, G74, G81-G89)
        if mode in ("G76", "G83", "G74", "G81", "G82", "G84", "G85", "G86", "G87", "G88", "G89"):
            if mode in ("G81", "G82", "G83", "G84", "G85", "G86", "G87", "G88", "G89") and active_plane == "G18":
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="G18_CANNED_CYCLE_NO_Y",
                    severity="ERROR",
                    message="G18 canned cycle is not possible on a machine without Y axis; LinuxCNC canned cycles in G18 feed along the normal Y axis. Use unrolled G0/G1 peck drilling.",
                    raw_line=stripped,
                ))
            if "Z" not in words:
                continue
            cycle_count += 1
            start_pt = (curr_z if curr_z is not None else 0.0, curr_x if curr_x is not None else 0.0)
            end_pt = (target_z if target_z is not None else start_pt[0], target_x if target_x is not None else start_pt[1])
            moves.append(BackplotMove(
                line_number=idx,
                mode=mode,
                start=start_pt,
                end=end_pt,
                tool_id=active_tool,
                feed=active_feed,
            ))
            continue

        if curr_z is None or curr_x is None:
            curr_z = target_z if target_z is not None else 0.0
            curr_x = target_x if target_x is not None else 0.0
            continue

        assert target_z is not None and target_x is not None
        start_pt = (curr_z, curr_x)
        end_pt = (target_z, target_x)
        seg_dist = math.hypot(end_pt[0] - start_pt[0], end_pt[1] - start_pt[1])

        if mode == "G0":
            rapid_count += 1
            if seg_dist < 1e-6:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="REDUNDANT_RAPID",
                    severity="WARNING",
                    message="Redundant zero-distance G0 rapid move",
                    raw_line=stripped,
                ))
            else:
                dz = abs(end_pt[0] - start_pt[0])
                dx = abs(end_pt[1] - start_pt[1])
                if stock is not None and dz > 0.05 and dx > 0.05:
                    seg_line = shapely.geometry.LineString([start_pt, end_pt])
                    stock_box = stock.to_shapely_box()
                    if seg_line.intersects(stock_box) and seg_line.intersection(stock_box).length > 0.5:
                        issues.append(GCodeIssue(
                            line_number=idx,
                            code="RAPID_DIAGONAL_IN_STOCK",
                            severity="ERROR",
                            message=f"Diagonal G0 rapid move (dZ={dz:.2f}, dX={dx:.2f}) crosses inside stock envelope",
                            raw_line=stripped,
                        ))

                if part_polygon is not None and not in_parting_op and not in_drilling_op:
                    seg_line = shapely.geometry.LineString([start_pt, end_pt])
                    eroded_part = part_polygon.buffer(-0.02)
                    if not eroded_part.is_empty and seg_line.intersects(eroded_part):
                        issues.append(GCodeIssue(
                            line_number=idx,
                            code="RAPID_PART_COLLISION",
                            severity="ERROR",
                            message="G0 rapid move collides with finished part geometry",
                            raw_line=stripped,
                        ))

            moves.append(BackplotMove(
                line_number=idx,
                mode="G0",
                start=start_pt,
                end=end_pt,
                tool_id=active_tool,
            ))

        elif mode in ("G1", "G33"):
            linear_count += 1
            if not spindle_running:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="CUT_WITHOUT_SPINDLE",
                    severity="ERROR",
                    message="Cutting move executed while spindle is off",
                    raw_line=stripped,
                ))
            if mode == "G1" and (active_feed is None or active_feed <= 0):
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="CUT_WITHOUT_FEED",
                    severity="ERROR",
                    message="G1 linear cut executed without active positive feedrate F",
                    raw_line=stripped,
                ))
            if seg_dist < 1e-6:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="ZERO_LENGTH_MOVE",
                    severity="WARNING",
                    message="Zero-length G1 linear move",
                    raw_line=stripped,
                ))

            if (
                part_polygon is not None
                and not in_parting_op
                and not in_threading_op
                and not in_drilling_op
                and mode == "G1"
            ):
                if in_computer_tnrc:
                    # Shift virtual tool tip (QUADRANT_3: -r, -r) back to physical nose center (+r, +r)
                    r = finishing_nose_radius_mm
                    c_start = (start_pt[0] + r, start_pt[1] + r)
                    c_end = (end_pt[0] + r, end_pt[1] + r)
                    swept_nose = shapely.geometry.LineString([c_start, c_end]).buffer(max(0.0, r - gouge_tol_mm))
                    eroded_part = part_polygon.buffer(-gouge_tol_mm)
                    if not eroded_part.is_empty and swept_nose.intersects(eroded_part):
                        gouge_area = swept_nose.intersection(eroded_part).area
                        if gouge_area > 0.02:
                            max_gouge = max(max_gouge, gouge_area)
                            issues.append(GCodeIssue(
                                line_number=idx,
                                code="CUT_PART_GOUGE",
                                severity="ERROR",
                                message=f"G1 TNRC move gouges finished part polygon (area {gouge_area:.3f}mm²)",
                                raw_line=stripped,
                            ))
                else:
                    seg_line = shapely.geometry.LineString([start_pt, end_pt])
                    eroded_part = part_polygon.buffer(-gouge_tol_mm)
                    if not eroded_part.is_empty and seg_line.intersects(eroded_part):
                        inter = seg_line.intersection(eroded_part)
                        gouge_len = inter.length
                        if gouge_len > 0.05:
                            max_gouge = max(max_gouge, gouge_len)
                            issues.append(GCodeIssue(
                                line_number=idx,
                                code="CUT_PART_GOUGE",
                                severity="ERROR",
                                message=f"G1 move gouges finished part polygon (overlap length {gouge_len:.3f}mm)",
                                raw_line=stripped,
                            ))

            moves.append(BackplotMove(
                line_number=idx,
                mode=mode,
                start=start_pt,
                end=end_pt,
                tool_id=active_tool,
                feed=active_feed,
            ))

        elif mode in ("G2", "G3"):
            arc_count += 1
            if not plane_g18_set:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="ARC_WITHOUT_G18",
                    severity="WARNING",
                    message="G2/G3 arc executed before G18 ZX plane selection",
                    raw_line=stripped,
                ))
            if not spindle_running:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="CUT_WITHOUT_SPINDLE",
                    severity="ERROR",
                    message="G2/G3 arc executed while spindle is off",
                    raw_line=stripped,
                ))

            i_off = words.get("I")
            k_off = words.get("K")
            if i_off is None or k_off is None:
                issues.append(GCodeIssue(
                    line_number=idx,
                    code="ARC_MISSING_CENTER",
                    severity="ERROR",
                    message="G2/G3 arc is missing incremental center offsets I and K",
                    raw_line=stripped,
                ))
            else:
                center_z = start_pt[0] + k_off
                center_x = start_pt[1] + i_off
                center_pt = (center_z, center_x)

                r_start = math.hypot(i_off, k_off)
                r_end = math.hypot(end_pt[0] - center_z, end_pt[1] - center_x)
                r_err = abs(r_start - r_end)
                max_arc_err = max(max_arc_err, r_err)

                if r_err > arc_radius_tol_mm:
                    issues.append(GCodeIssue(
                        line_number=idx,
                        code="ARC_RADIUS_MISMATCH",
                        severity="ERROR",
                        message=f"Arc start radius ({r_start:.4f}mm) != end radius ({r_end:.4f}mm), diff={r_err:.4f}mm",
                        raw_line=stripped,
                    ))

                if r_start > max_arc_radius_mm or r_start < 0.05:
                    issues.append(GCodeIssue(
                        line_number=idx,
                        code="ARC_RUNAWAY_RADIUS",
                        severity="ERROR",
                        message=f"Bogus/runaway arc radius R={r_start:.3f}mm (allowed [0.05, {max_arc_radius_mm:.1f}]mm)",
                        raw_line=stripped,
                    ))

                arc_pts, sweep_deg = _sample_arc_points(
                    start_pt, end_pt, center_pt, mode, xz_arc_chirality=xz_arc_chirality
                )
                for pz, px in arc_pts:
                    all_z.append(pz)
                    all_x.append(px)

                if sweep_deg > 185.0:
                    issues.append(GCodeIssue(
                        line_number=idx,
                        code="ARC_EXCESSIVE_SWEEP",
                        severity="ERROR",
                        message=f"Arc sweeps {sweep_deg:.1f}° (>185°), indicating inverted G2/G3 chirality or full-circle loop",
                        raw_line=stripped,
                    ))

                if part_polygon is not None:
                    if in_computer_tnrc:
                        r = finishing_nose_radius_mm
                        shifted_arc = [(pz + r, px + r) for pz, px in arc_pts]
                        swept_nose = shapely.geometry.LineString(shifted_arc).buffer(max(0.0, r - gouge_tol_mm))
                        eroded_part = part_polygon.buffer(-gouge_tol_mm)
                        if not eroded_part.is_empty and swept_nose.intersects(eroded_part):
                            gouge_area = swept_nose.intersection(eroded_part).area
                            if gouge_area > 0.02:
                                max_gouge = max(max_gouge, gouge_area)
                                issues.append(GCodeIssue(
                                    line_number=idx,
                                    code="CUT_PART_GOUGE",
                                    severity="ERROR",
                                    message=f"{mode} TNRC arc gouges finished part polygon (area {gouge_area:.3f}mm²)",
                                    raw_line=stripped,
                                ))
                    else:
                        arc_line = shapely.geometry.LineString(arc_pts)
                        eroded_part = part_polygon.buffer(-gouge_tol_mm)
                        if not eroded_part.is_empty and arc_line.intersects(eroded_part):
                            inter = arc_line.intersection(eroded_part)
                            if inter.length > 0.05:
                                max_gouge = max(max_gouge, inter.length)
                                issues.append(GCodeIssue(
                                    line_number=idx,
                                    code="CUT_PART_GOUGE",
                                    severity="ERROR",
                                    message=f"{mode} arc gouges finished part polygon (overlap {inter.length:.3f}mm)",
                                    raw_line=stripped,
                                ))

                moves.append(BackplotMove(
                    line_number=idx,
                    mode=mode,
                    start=start_pt,
                    end=end_pt,
                    center=center_pt,
                    radius=r_start,
                    sweep_deg=sweep_deg,
                    tool_id=active_tool,
                    feed=active_feed,
                ))

        curr_z = target_z
        curr_x = target_x

    bbox = (
        min(all_z) if all_z else 0.0,
        min(all_x) if all_x else 0.0,
        max(all_z) if all_z else 0.0,
        max(all_x) if all_x else 0.0,
    )
    has_errors = any(i.severity == "ERROR" for i in issues)
    return VerificationReport(
        is_valid=not has_errors,
        issues=issues,
        moves=moves,
        total_lines=total_lines,
        rapid_count=rapid_count,
        linear_count=linear_count,
        arc_count=arc_count,
        cycle_count=cycle_count,
        max_arc_radius_error_mm=max_arc_err,
        max_part_gouge_mm=max_gouge,
        bounding_box=bbox,
    )
