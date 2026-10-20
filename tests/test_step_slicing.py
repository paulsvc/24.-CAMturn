from __future__ import annotations

from pathlib import Path
import pytest

from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf, gp_Vec
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs

from lathecam.cad.face import FaceType, decompose_contour_into_faces
from lathecam.cad.step_importer import STEPImporter
from lathecam.cam.roughing import generate_roughing_toolpath
from lathecam.cam.shadowing import compute_shadowed_polygon
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


def _save_shape_as_step(shape, filepath: Path) -> Path:
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(str(filepath))
    return filepath


def test_step_cylinder_slicing(tmp_path: Path) -> None:
    # Cylinder radius 12.0 mm, height 30.0 mm along Z
    cyl = BRepPrimAPI_MakeCylinder(12.0, 30.0).Shape()
    step_file = _save_shape_as_step(cyl, tmp_path / "cylinder.step")

    importer = STEPImporter(deflection_tolerance_mm=0.005)
    contour = importer.extract_contour(step_file, spindle_axis="z")

    assert contour is not None
    assert len(contour.points) >= 2
    # Front face re-zeroed to 0.0
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    # Length along Z is 30mm, so z_min should be -30mm
    assert pytest.approx(contour.z_min, abs=0.1) == -30.0
    # Radius should be 12.0mm
    assert pytest.approx(contour.x_max, abs=0.1) == 12.0


def test_step_stepped_shaft_slicing(tmp_path: Path) -> None:
    # Two fused cylinders forming a stepped turned shaft:
    # Front step: radius 10mm, length 20mm (from Z=0 to 20)
    # Rear step: radius 18mm, length 25mm (from Z=20 to 45)
    cyl1 = BRepPrimAPI_MakeCylinder(10.0, 20.0).Shape()

    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(0, 0, 20))
    cyl2_raw = BRepPrimAPI_MakeCylinder(18.0, 25.0).Shape()
    cyl2 = BRepBuilderAPI_Transform(cyl2_raw, trsf).Shape()

    stepped = BRepAlgoAPI_Fuse(cyl1, cyl2).Shape()
    step_file = _save_shape_as_step(stepped, tmp_path / "stepped_shaft.step")

    importer = STEPImporter()
    contour = importer.extract_contour(step_file, spindle_axis="auto")

    assert contour is not None
    # Front face at 0.0
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    # Total length is 20 + 25 = 45mm
    assert pytest.approx(contour.z_min, abs=0.1) == -45.0
    # Radii: minimum radius should be 10.0mm, maximum radius should be 18.0mm
    assert pytest.approx(contour.x_min, abs=0.1) == 10.0
    assert pytest.approx(contour.x_max, abs=0.1) == 18.0


def test_step_to_cam_roughing_pipeline(tmp_path: Path) -> None:
    # Create stepped shaft and run end-to-end through CAM kernel
    cyl1 = BRepPrimAPI_MakeCylinder(8.0, 15.0).Shape()
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(0, 0, 15))
    cyl2_raw = BRepPrimAPI_MakeCylinder(14.0, 20.0).Shape()
    cyl2 = BRepBuilderAPI_Transform(cyl2_raw, trsf).Shape()

    shaft = BRepAlgoAPI_Fuse(cyl1, cyl2).Shape()
    step_file = _save_shape_as_step(shaft, tmp_path / "cam_test.step")

    importer = STEPImporter()
    contour = importer.extract_contour(step_file)

    # Verify shadowed polygon works without error
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)
    shadowed_poly = compute_shadowed_polygon(contour.points, tool)
    assert shadowed_poly.is_valid
    assert not shadowed_poly.is_empty

    # Verify roughing toolpath generation
    stock = Stock(od_mm=32.0, z_start_mm=1.0, z_end_mm=-40.0)
    rough_cmds = generate_roughing_toolpath(
        profile_pts=contour.points,
        stock=stock,
        tool=tool,
        doc_mm=2.0,
        finish_allowance_mm=0.5,
    )
    assert len(rough_cmds) > 0
    assert any(c.mode == "G1" for c in rough_cmds)


def test_step_hollow_cylinder_slicing(tmp_path: Path) -> None:
    # Outer cylinder R=25.0mm, Length=60.0mm; Inner bore R=15.0mm (Through-hole)
    outer = BRepPrimAPI_MakeCylinder(25.0, 60.0).Shape()
    inner = BRepPrimAPI_MakeCylinder(15.0, 60.0).Shape()
    tube = BRepAlgoAPI_Cut(outer, inner).Shape()

    step_file = _save_shape_as_step(tube, tmp_path / "tube.step")
    importer = STEPImporter()
    contour = importer.extract_contour(step_file, spindle_axis="z")

    assert contour is not None
    assert contour.is_closed
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    assert pytest.approx(contour.z_min, abs=0.1) == -60.0
    # Hole radius should be preserved as x_min, OD as x_max
    assert pytest.approx(contour.x_min, abs=0.1) == 15.0
    assert pytest.approx(contour.x_max, abs=0.1) == 25.0

    # Verify face decomposition identifies OD cylinder, ID bore, and end faces
    faces = decompose_contour_into_faces(contour)
    assert len(faces) == 4
    face_types = [f.face_type for f in faces]
    assert FaceType.CYLINDER in face_types or FaceType.GROOVE in face_types
    assert FaceType.SHOULDER in face_types


def test_step_part1_workspace_file() -> None:
    part1_path = Path("step/Part1.STEP")
    if not part1_path.is_file():
        pytest.skip("step/Part1.STEP not found in workspace")

    importer = STEPImporter()
    contour = importer.extract_contour(part1_path, spindle_axis="auto")

    assert contour is not None
    assert contour.is_closed
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    assert pytest.approx(contour.z_min, abs=0.5) == -100.0
    # Hole radius ~41.42mm, OD radius ~71.89mm
    assert pytest.approx(contour.x_min, abs=0.5) == 41.42
    assert pytest.approx(contour.x_max, abs=0.5) == 71.89

    faces = decompose_contour_into_faces(contour)
    assert len(faces) == 4

