"""Unit tests for ISO Insert Shapes & Tool Library Editor."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from PySide6.QtWidgets import QApplication

from lathecam.cam.tools import (
    LatheTool,
    ISO_SHAPE_DESCRIPTIONS,
    ISO_INSERT_PRESETS,
)
from lathecam.cam.tool_mesh import build_tool_3d_meshes
from lathecam.models.project import LatheProject
from lathecam.ui.dialogs.tool_library_dialog import ToolLibraryDialog, Insert2DPreviewWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_lathe_tool_iso_defaults():
    tool = LatheTool(tool_id=1, name="Test CNMG", insert_shape="C")
    assert tool.insert_shape == "C"
    assert tool.inscribed_circle_mm == 12.7
    assert tool.thickness_mm == 4.76
    assert tool.cutting_edge_length_mm == 12.0
    assert tool.hand == "R"

    data = tool.to_dict()
    assert data["insert_shape"] == "C"
    assert data["inscribed_circle_mm"] == 12.7

    restored = LatheTool.from_dict(data)
    assert restored.tool_id == tool.tool_id
    assert restored.insert_shape == "C"
    assert restored.inscribed_circle_mm == 12.7
    assert restored.thickness_mm == 4.76


def test_iso_presets_application():
    assert len(ISO_INSERT_PRESETS) >= 10
    tool = LatheTool(tool_id=1, name="Preset Tool")
    
    for preset_name, preset_data in ISO_INSERT_PRESETS.items():
        tool.apply_preset(preset_name)
        assert tool.insert_shape == preset_data.get("insert_shape", tool.insert_shape)
        if "inscribed_circle_mm" in preset_data:
            assert tool.inscribed_circle_mm == preset_data["inscribed_circle_mm"]
        if "nose_radius_mm" in preset_data:
            assert tool.nose_radius_mm == preset_data["nose_radius_mm"]


def test_3d_mesh_generation_all_iso_shapes():
    shapes = list(ISO_SHAPE_DESCRIPTIONS.keys())
    assert len(shapes) >= 11
    
    for shape in shapes:
        tool = LatheTool(
            tool_id=1,
            name=f"Tool {shape}",
            insert_shape=shape,
            inscribed_circle_mm=12.7,
            nose_radius_mm=0.8,
            thickness_mm=4.76,
            tip_width_mm=3.0,
        )
        insert_mesh, holder_mesh = build_tool_3d_meshes(tool)
        assert insert_mesh is not None, f"Insert mesh for {shape} is None"
        assert insert_mesh.n_points > 0, f"Insert mesh for {shape} has 0 points"
        assert holder_mesh is not None, f"Holder mesh for {shape} is None"
        assert holder_mesh.n_points > 0, f"Holder mesh for {shape} has 0 points"


def test_project_tools_serialization(tmp_path: Path):
    proj = LatheProject.create_demo_project()
    t1 = proj.tools[1]
    t1.apply_preset("VNMG 160404")
    t1.name = "Custom Finishing V"
    
    save_path = tmp_path / "project_with_tools.lcam"
    proj.save_to_file(save_path)
    
    loaded = LatheProject.load_from_file(save_path)
    assert 1 in loaded.tools
    assert loaded.tools[1].name == "Custom Finishing V"
    assert loaded.tools[1].insert_shape == "V"
    assert loaded.tools[1].inscribed_circle_mm == 9.525
    assert loaded.tools[1].nose_radius_mm == 0.4


def test_insert_2d_preview_widget(qapp):
    widget = Insert2DPreviewWidget()
    tool = LatheTool(tool_id=1, name="D Tool", insert_shape="D", inscribed_circle_mm=12.7, nose_radius_mm=0.4)
    widget.set_tool(tool)
    widget.resize(300, 300)
    # Trigger a paint event
    widget.repaint()
    assert widget._tool.insert_shape == "D"


def test_tool_library_dialog_crud(qapp, tmp_path: Path):
    proj = LatheProject.create_demo_project()
    dialog = ToolLibraryDialog(project=proj)
    
    # Verify initial table count matches project tools
    assert dialog.table.rowCount() == len(proj.tools)
    
    # Select first row
    dialog.table.selectRow(0)
    assert dialog.txt_name.text() != ""
    
    # Change preset
    wnmg_idx = dialog.combo_preset.findData("WNMG 080408")
    assert wnmg_idx >= 0
    dialog.combo_preset.setCurrentIndex(wnmg_idx)
    assert dialog.combo_shape.currentData() == "W"
    
    # Add new tool
    initial_count = len(dialog._tools)
    dialog._action_add_tool()
    assert len(dialog._tools) == initial_count + 1
    
    # Duplicate tool
    dialog.table.selectRow(dialog.table.rowCount() - 1)
    dialog._action_duplicate_tool()
    assert len(dialog._tools) == initial_count + 2
    
    # Delete tool
    dialog.table.selectRow(dialog.table.rowCount() - 1)
    dialog._action_delete_tool()
    assert len(dialog._tools) == initial_count + 1
    
    # Apply changes to project
    dialog._action_apply()
    assert len(proj.tools) == initial_count + 1
    dialog.close()
