from __future__ import annotations

import math
import pytest
import shapely.geometry

from lathecam.cam.shadowing import (
    compute_shadowed_polygon,
    compute_shadowed_profile,
    profile_to_polygon,
)
from lathecam.cam.tools import LatheTool, ToolOrientation


def test_profile_to_polygon_valid() -> None:
    # Simple stepped shaft profile: (Z, X_radius)
    profile = [(0.0, 10.0), (-10.0, 10.0), (-10.0, 20.0), (-30.0, 20.0)]
    poly = profile_to_polygon(profile)

    assert poly.is_valid
    assert not poly.is_empty
    min_z, min_x, max_z, max_x = poly.bounds
    assert pytest.approx(min_z) == -30.0
    assert pytest.approx(max_z) == 0.0
    assert pytest.approx(min_x) == 0.0
    assert pytest.approx(max_x) == 20.0


def test_undercut_groove_shadowing() -> None:
    # Profile with an undercut groove:
    # Outer OD = 15mm from Z=0 to Z=-10
    # Groove drops to OD = 10mm from Z=-10 to Z=-15
    # OD returns to 15mm from Z=-15 to Z=-25
    profile = [
        (0.0, 15.0),
        (-10.0, 15.0),
        (-10.0, 10.0),  # Steep vertical drop
        (-15.0, 10.0),  # Groove floor
        (-15.0, 15.0),  # Back wall
        (-25.0, 15.0),
    ]

    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)
    # CNMG clearance angle is 5 degrees
    assert tool.clearance_angle_deg == 5.0

    shadowed_poly = compute_shadowed_polygon(profile, tool)
    assert shadowed_poly.is_valid

    # The original base polygon is inside the shadowed polygon
    base_poly = profile_to_polygon(profile)
    assert shadowed_poly.contains(base_poly) or shadowed_poly.covers(base_poly)

    # In the groove region (e.g. Z = -12.5), the shadowed radius should be > 10.0
    # Specifically, with 5 deg clearance slope:
    # Drop over 2.5mm from Z=-10 is 2.5 * tan(5 deg) = 2.5 * 0.08749 = 0.218mm
    # So expected radius at Z=-12.5 should be approximately 15.0 - 0.22 = 14.78mm >> 10.0mm!
    test_pt = shapely.geometry.Point(-12.5, 12.0)
    assert shadowed_poly.contains(test_pt), "Groove under-shadow should be filled in by clearance wedge"

    # Extract top profile and verify groove depth is bridged
    shadowed_pts = compute_shadowed_profile(profile, tool, sample_step_mm=0.5)
    assert len(shadowed_pts) > 0
    for z, x in shadowed_pts:
        if -15.0 <= z <= -10.0:
            assert x > 14.0, f"Shadowed profile at Z={z:.1f} should bridge groove, got X={x:.2f}"


def test_tool_virtual_tip_orientations() -> None:
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)
    r = 0.8

    tool.orientation = ToolOrientation.QUADRANT_1
    assert tool.virtual_tip_offset() == (+r, +r)

    tool.orientation = ToolOrientation.QUADRANT_2
    assert tool.virtual_tip_offset() == (-r, +r)

    tool.orientation = ToolOrientation.QUADRANT_3
    assert tool.virtual_tip_offset() == (-r, -r)

    tool.orientation = ToolOrientation.QUADRANT_4
    assert tool.virtual_tip_offset() == (+r, -r)

    tool.orientation = ToolOrientation.QUADRANT_9
    assert tool.virtual_tip_offset() == (0.0, 0.0)
