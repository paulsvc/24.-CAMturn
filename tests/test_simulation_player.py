from __future__ import annotations

import pytest
import pyvista as pv

from lathecam.cam.tool_mesh import SimFrame, build_simulation_trajectory, build_tool_3d_meshes
from lathecam.cam.tools import LatheTool
from lathecam.models.project import LatheProject


def test_tool_3d_meshes_generation():
    """Verify all tool insert and shank shapes generate valid, non-empty 3D meshes."""
    tools = [
        LatheTool.cnmg_roughing(),
        LatheTool.dnmg_finishing(),
        LatheTool.vnmg_profiling(),
        LatheTool.parting_blade(width_mm=3.0),
        LatheTool.threading_tool(),
        LatheTool.center_drill(diameter_mm=5.0),
        None,  # Fallback default
    ]

    for tool in tools:
        insert_mesh, shank_mesh = build_tool_3d_meshes(tool)

        assert isinstance(insert_mesh, pv.PolyData)
        assert isinstance(shank_mesh, pv.PolyData)

        assert insert_mesh.n_points > 0
        assert insert_mesh.n_cells > 0
        assert shank_mesh.n_points > 0
        assert shank_mesh.n_cells > 0

        # Cutting tip / apex must be near origin (0, 0, 0)
        bounds = insert_mesh.bounds
        assert bounds[0] <= 1e-4  # x_min near 0
        assert bounds[4] <= 1e-4  # z_min near 0


def test_simulation_trajectory_demo_project():
    """Verify trajectory building produces smooth, sequential frames across all operations."""
    project = LatheProject.create_demo_project()
    project.recalculate_all()

    traj = build_simulation_trajectory(project)
    assert len(traj) > 2000

    # Verify frame fields
    modes = set()
    tool_ids = set()
    for f in traj:
        assert isinstance(f, SimFrame)
        assert isinstance(f.z, float)
        assert isinstance(f.x, float)
        # Radius can be slightly negative when facing past centerline to clear pip
        assert f.x >= -3.0
        modes.add(f.mode)
        tool_ids.add(f.tool_id)

    # Must contain various motion modes
    assert "G0" in modes
    assert "G1" in modes
    # Must utilize multiple tools (roughing, finishing, threading, drilling, parting)
    assert len(tool_ids) >= 3


def test_simulation_trajectory_single_operation():
    """Verify trajectory building scoped to a single operation."""
    project = LatheProject.create_demo_project()
    project.recalculate_all()

    first_op = project.operations[0]
    traj = build_simulation_trajectory(project, op_id=first_op.op_id)

    assert len(traj) > 0
    assert len(traj) < 2000
    for f in traj:
        assert f.op_name == first_op.name
        assert f.tool_id == first_op.tool_id


def test_simulation_viewport_playback_logic():
    """Test viewport simulation state management and playback methods in Qt environment."""
    from PySide6.QtWidgets import QApplication
    from lathecam.ui.viewport.vtk_viewport import VTKLatheViewport

    app = QApplication.instance() or QApplication([])

    viewport = VTKLatheViewport()
    project = LatheProject.create_demo_project()
    project.recalculate_all()

    viewport.render_project(project)

    # Initial state
    assert len(viewport._sim_trajectory) > 0
    assert viewport._sim_frame_idx == 0
    assert not viewport._sim_playing
    assert viewport.slider_sim.maximum() == len(viewport._sim_trajectory) - 1

    # Play
    viewport.sim_play()
    assert viewport._sim_playing
    assert viewport._sim_timer.isActive()

    # Pause
    viewport.sim_pause()
    assert not viewport._sim_playing
    assert not viewport._sim_timer.isActive()

    # Step forward / backward
    viewport.sim_step(15)
    assert viewport._sim_frame_idx == 15

    viewport.sim_step(-5)
    assert viewport._sim_frame_idx == 10

    # Stop rewinds to 0
    viewport.sim_stop()
    assert viewport._sim_frame_idx == 0
    assert not viewport._sim_playing
