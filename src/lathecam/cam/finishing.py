from __future__ import annotations

from enum import Enum
from typing import Sequence
import math
import numpy as np
import pyclipper
import shapely.geometry

from lathecam.cad.geometry import Point2D, fit_arcs_to_polyline, resample_polyline
from lathecam.cam.commands import MotionCmd
from lathecam.cam.shadowing import compute_shadowed_profile
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


class CompensationMode(Enum):
    CONTROLLER = "controller"  # G41 / G42 with machine tool table
    COMPUTER = "computer"      # CAM-calculated TNRC offset + virtual tip shift


def offset_profile_pyclipper(
    points: Sequence[Point2D],
    offset_mm: float,
    scale: float = 1e6,
) -> list[Point2D]:
    """Applies a 2D parallel curve offset using PyClipper with integer scaling.
    
    Points are in (Z, X) space.
    """
    if len(points) < 2:
        return list(points)

    # Scale to integer coords for PyClipper
    scaled_path = [[int(round(z * scale)), int(round(x * scale))] for z, x in points]

    pco = pyclipper.PyclipperOffset()
    pco.AddPath(scaled_path, pyclipper.JT_ROUND, pyclipper.ET_OPENROUND)
    # Execute offset
    solution = pco.Execute(offset_mm * scale)

    if not solution:
        # Fallback to shapely offset_curve if pyclipper open path offset returns empty
        ls = shapely.geometry.LineString(points)
        try:
            offset_ls = shapely.offset_curve(ls, distance=offset_mm, quad_segs=16, join_style="round")
            return list(offset_ls.coords)
        except Exception:
            return list(points)

    # Find longest path in solution
    best_path = max(solution, key=len)
    offset_pts = [(pt[0] / scale, pt[1] / scale) for pt in best_path]

    # Maintain directional continuity from +Z to -Z
    if len(offset_pts) >= 2 and offset_pts[0][0] < offset_pts[-1][0]:
        offset_pts.reverse()

    return offset_pts


def generate_finishing_toolpath(
    profile_pts: Sequence[Point2D],
    stock: Stock,
    tool: LatheTool,
    comp_mode: CompensationMode = CompensationMode.COMPUTER,
    feed_mm_rev: float = 0.12,
    lead_in_mm: float = 2.0,
    retract_mm: float = 1.0,
    chordal_tolerance_mm: float = 0.005,
    sample_step_mm: float = 0.25,
) -> list[MotionCmd]:
    """Generates an OD profile finishing toolpath with G2/G3 arc reconstruction and TNRC."""
    # 1. Compute shadowed reachable profile
    shadowed_pts = compute_shadowed_profile(
        profile_pts,
        tool,
        sample_step_mm=sample_step_mm,
        z_min_bound=stock.z_end_mm,
        z_max_bound=stock.z_start_mm,
    )

    if len(shadowed_pts) < 2:
        return [MotionCmd.comment("Error: Invalid profile geometry for finishing")]

    # Ensure profile runs from front (+Z) to rear (-Z)
    if shadowed_pts[0][0] < shadowed_pts[-1][0]:
        shadowed_pts.reverse()

    commands: list[MotionCmd] = []
    commands.append(MotionCmd.comment(f"Begin Profile Finishing Pass ({comp_mode.value.upper()} Comp, Feed: {feed_mm_rev:.3f}mm/rev)"))

    safe_x = stock.od_radius + 2.0
    safe_z = stock.z_start_mm + 2.0

    if comp_mode == CompensationMode.CONTROLLER:
        # Controller Mode: Follow exact part geometry with G42 lead-in and G40 lead-out
        fitted_segments = fit_arcs_to_polyline(shadowed_pts, chordal_tolerance_mm=chordal_tolerance_mm)
        if not fitted_segments:
            return [MotionCmd.comment("Error fitting segments to profile")]

        first_pt = fitted_segments[0].start
        lead_in_pt = (first_pt[0] + lead_in_mm, first_pt[1] + lead_in_mm)

        # Rapid to clearance
        commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))
        commands.append(MotionCmd.rapid(x=lead_in_pt[1], z=lead_in_pt[0]))

        # Activate G42 (cutter comp right for OD turning toward chuck)
        commands.append(MotionCmd(mode="G42", x=first_pt[1], z=first_pt[0], f=feed_mm_rev))

        # Output profile moves
        for seg in fitted_segments:
            commands.append(seg.to_motion_cmd(feed=feed_mm_rev))

        # 45-degree retract and cancel compensation with G40
        last_pt = fitted_segments[-1].end
        retract_pt = (last_pt[0] + retract_mm, last_pt[1] + retract_mm)
        commands.append(MotionCmd(mode="G40", x=retract_pt[1], z=retract_pt[0], f=feed_mm_rev * 1.5))
        commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))

    else:
        # Computer Mode: Parallel offset by nose radius + virtual tool-tip vector shift
        r = tool.nose_radius_mm
        # Offset curve outward in +X direction (for OD profile, distance is +r)
        offset_pts = offset_profile_pyclipper(shadowed_pts, offset_mm=r)

        # Shift all vertices by virtual tool tip offset
        dz, dx = tool.virtual_tip_offset()
        shifted_pts = [(z + dz, x + dx) for z, x in offset_pts]

        # Resample and fit G2/G3 arcs
        smooth_pts = resample_polyline(shifted_pts, step_mm=0.2)
        fitted_segments = fit_arcs_to_polyline(smooth_pts, chordal_tolerance_mm=chordal_tolerance_mm)

        if not fitted_segments:
            fitted_segments = [seg for seg in fit_arcs_to_polyline(shifted_pts, chordal_tolerance_mm=chordal_tolerance_mm)]

        if not fitted_segments:
            return [MotionCmd.comment("Error fitting segments to compensated profile")]

        first_pt = fitted_segments[0].start
        lead_in_pt = (first_pt[0] + lead_in_mm, first_pt[1] + lead_in_mm)

        # Rapids and approach
        commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))
        commands.append(MotionCmd.rapid(x=lead_in_pt[1], z=lead_in_pt[0]))
        commands.append(MotionCmd.linear(x=first_pt[1], z=first_pt[0], f=feed_mm_rev))

        # Cut along profile
        for seg in fitted_segments:
            commands.append(seg.to_motion_cmd(feed=feed_mm_rev))

        # 45-degree clearance retract
        last_pt = fitted_segments[-1].end
        commands.append(MotionCmd.linear(x=last_pt[1] + retract_mm, z=last_pt[0] + retract_mm, f=feed_mm_rev * 1.5))
        commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))

    commands.append(MotionCmd.comment("End Profile Finishing Pass"))
    return commands
