from __future__ import annotations

import math
import pytest
import numpy as np

from lathecam.cad.geometry import (
    ArcSegment,
    LineSegment,
    fit_arcs_to_polyline,
)
from lathecam.cam.finishing import CompensationMode, generate_finishing_toolpath
from lathecam.cam.operations import DrillingOp, FacingOp, PartingOp, ThreadingOp
from lathecam.cam.roughing import generate_roughing_toolpath
from lathecam.cam.shadowing import profile_to_polygon
from lathecam.cam.simulator import simulate_2d_material_removal
from lathecam.cam.tools import LatheTool, ToolOrientation
from lathecam.models.stock import Stock


def test_arc_fitting_reconstruction() -> None:
    # 1. Test pure straight line fitting
    straight_line = [(0.0, 10.0), (-5.0, 10.0), (-10.0, 10.0), (-15.0, 10.0)]
    fitted_lines = fit_arcs_to_polyline(straight_line, chordal_tolerance_mm=0.005)
    assert len(fitted_lines) == 1
    assert isinstance(fitted_lines[0], LineSegment)
    assert fitted_lines[0].start == (0.0, 10.0)
    assert fitted_lines[0].end == (-15.0, 10.0)

    # 2. Test circular fillet reconstruction
    # Fillet centered at Z = -10, X = 15 with radius R = 5.0
    # Sweeping from (Z=-10, X=20) clockwise to (Z=-5, X=15)
    theta = np.linspace(math.pi / 2, 0.0, 15)  # 90 deg arc
    arc_points = [(-10.0 + 5.0 * math.cos(t), 15.0 + 5.0 * math.sin(t)) for t in theta]

    fitted_arc = fit_arcs_to_polyline(arc_points, chordal_tolerance_mm=0.005)
    assert len(fitted_arc) >= 1
    assert any(isinstance(seg, ArcSegment) for seg in fitted_arc)

    # Check fitted parameters
    arc_seg = [s for s in fitted_arc if isinstance(s, ArcSegment)][0]
    assert pytest.approx(arc_seg.radius, abs=0.05) == 5.0
    assert pytest.approx(arc_seg.center[0], abs=0.05) == -10.0
    assert pytest.approx(arc_seg.center[1], abs=0.05) == 15.0


def test_roughing_toolpath_generation() -> None:
    # Stock: OD = 40mm (radius 20mm), Z from +1.0 to -30.0
    stock = Stock(od_mm=40.0, z_start_mm=1.0, z_end_mm=-30.0)
    # Part: Stepped shaft, OD=20mm (radius 10mm) from Z=0 to -15, OD=30mm (radius 15mm) from -15 to -30
    profile = [(0.0, 10.0), (-15.0, 10.0), (-15.0, 15.0), (-30.0, 15.0)]

    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)

    commands = generate_roughing_toolpath(
        profile_pts=profile,
        stock=stock,
        tool=tool,
        doc_mm=2.0,
        feed_mm_rev=0.25,
        finish_allowance_mm=0.5,
        retract_mm=0.8,
    )

    assert len(commands) > 0

    # Verify that roughing passes have cutting moves along -Z
    cut_moves = [c for c in commands if c.mode == "G1" and c.z is not None]
    assert len(cut_moves) > 0

    # Verify 45-degree clearance retracts: a move with both +dZ and +dX
    has_retract = False
    for i in range(len(commands) - 1):
        c1 = commands[i]
        c2 = commands[i + 1]
        if c1.mode == "G1" and c2.mode == "G1":
            if c1.z is not None and c2.z is not None and c1.x is not None and c2.x is not None:
                if c2.z > c1.z and c2.x > c1.x:  # Retracting away from chuck (+dZ) and outward (+dX)
                    has_retract = True
                    break
    assert has_retract, "Roughing passes must include a 45-degree clearance retract"


def test_finishing_toolpath_modes() -> None:
    stock = Stock(od_mm=40.0, z_start_mm=0.0, z_end_mm=-30.0)
    profile = [(0.0, 10.0), (-15.0, 10.0), (-15.0, 15.0), (-30.0, 15.0)]
    tool = LatheTool.dnmg_finishing(tool_id=2, nose_radius_mm=0.4)

    # Controller Compensation mode (G42 / G40)
    ctrl_cmds = generate_finishing_toolpath(
        profile_pts=profile,
        stock=stock,
        tool=tool,
        comp_mode=CompensationMode.CONTROLLER,
    )
    modes = [c.mode for c in ctrl_cmds]
    assert "G42" in modes
    assert "G40" in modes

    # Computer Compensation mode (TNRC)
    comp_cmds = generate_finishing_toolpath(
        profile_pts=profile,
        stock=stock,
        tool=tool,
        comp_mode=CompensationMode.COMPUTER,
    )
    assert len(comp_cmds) > 0
    # In computer mode, G42/G40 are not emitted because the path itself is offset
    comp_modes = [c.mode for c in comp_cmds]
    assert "G42" not in comp_modes
    assert "G40" not in comp_modes


def test_parametric_operations() -> None:
    stock = Stock(od_mm=30.0, z_start_mm=2.0, z_end_mm=-25.0)
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)

    # 1. FacingOp: check plunge past centerline
    facing = FacingOp(stock=stock, tool=tool, stepover_z_mm=1.0)
    f_cmds = facing.generate()
    plunge_cmds = [c for c in f_cmds if c.mode == "G1" and c.x is not None]
    assert any(c.x < 0.0 for c in plunge_cmds), "Facing must plunge past centerline to -nose_radius"

    # 2. ThreadingOp: check G76 and G33 preview
    threading = ThreadingOp(pitch_mm=1.5, major_dia_mm=20.0, z_start_mm=0.0, z_end_mm=-15.0)
    th_cmds = threading.generate()
    g76_cmds = [c for c in th_cmds if c.mode == "G76"]
    assert len(g76_cmds) == 1
    assert g76_cmds[0].raw_params["p"] == 1.5
    assert g76_cmds[0].raw_params["z"] == -15.0

    preview_cmds = threading.generate_unrolled_g33_preview()
    g33_moves = [c for c in preview_cmds if c.mode == "G33"]
    assert len(g33_moves) >= 2, "Unrolled threading preview must contain synchronized G33 passes"

    # 3. PartingOp: check peck increments
    parting_tool = LatheTool.parting_blade(tool_id=4, width_mm=3.0)
    parting = PartingOp(stock=stock, tool=parting_tool, target_z_mm=-20.0, target_x_radius_mm=0.0, peck_depth_mm=1.5)
    p_cmds = parting.generate()
    plunges = [c for c in p_cmds if c.mode == "G1" and c.x is not None]
    assert len(plunges) >= 5, "Parting should perform multiple pecks to reach X=0.0"

    # 4. DrillingOp: check centerline positioning, constant RPM, and G83 cycle
    drill = DrillingOp(z_depth_mm=-25.0, peck_q_mm=3.0, feed_mm_rev=0.15, rpm=1200)
    d_cmds = drill.generate()
    d_modes = [c.mode for c in d_cmds]
    assert "SPINDLE_RPM" in d_modes
    assert "G83" in d_modes
    assert "G80" in d_modes


def test_2d_material_removal_simulation() -> None:
    stock = Stock(od_mm=30.0, z_start_mm=0.0, z_end_mm=-20.0)
    profile = [(0.0, 10.0), (-20.0, 10.0)]
    part_poly = profile_to_polygon(profile, z_min=-20.0, z_max=0.0)
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)

    rough_cmds = generate_roughing_toolpath(
        profile_pts=profile,
        stock=stock,
        tool=tool,
        doc_mm=2.0,
        finish_allowance_mm=0.0,
    )

    sim = simulate_2d_material_removal(stock, part_poly, rough_cmds, tool)
    assert not sim.remaining_stock.is_empty
    # Gouge area should be zero / within numeric tolerance
    assert sim.gouge_area_mm2 < 1e-3
    assert not sim.is_gouged


def test_multipocket_roughing() -> None:
    # Stock: OD 40mm (radius 20mm), Z=0 to -30
    stock = Stock(od_mm=40.0, z_start_mm=0.0, z_end_mm=-30.0)
    # Profile with a center raised collar (creates two separate pockets at X < 18):
    # Front pocket: Z=0 to -10, radius 10
    # Center collar: Z=-10 to -20, radius 18
    # Rear pocket: Z=-20 to -30, radius 10
    profile = [
        (0.0, 10.0),
        (-10.0, 10.0),
        (-10.0, 18.0),
        (-20.0, 18.0),
        (-20.0, 10.0),
        (-30.0, 10.0),
    ]
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)

    cmds = generate_roughing_toolpath(
        profile_pts=profile,
        stock=stock,
        tool=tool,
        doc_mm=2.0,
        finish_allowance_mm=0.5,
    )

    assert len(cmds) > 0
    # Verify both pockets are cut
    # Look for cuts in the front pocket (Z around -5) and rear pocket (Z around -25)
    g1_moves = [c for c in cmds if c.mode == "G1" and c.z is not None]
    z_coords = [c.z for c in g1_moves]
    assert any(-10.0 <= z <= 0.0 for z in z_coords), "Should cut front pocket"
    assert any(-30.0 <= z <= -20.0 for z in z_coords), "Should cut rear pocket"

