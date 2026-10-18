from __future__ import annotations

import math
from pathlib import Path
import pytest
import ezdxf

from lathecam.cad.dxf_importer import DXFImporter
from lathecam.cam.finishing import generate_finishing_toolpath, CompensationMode
from lathecam.cam.roughing import generate_roughing_toolpath
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


def test_dxf_polyline_with_bulge(tmp_path: Path) -> None:
    # Create DXF with LWPOLYLINE containing straight lines and an arc fillet
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Part geometry along X (as Z) and Y (as X_radius):
    # (0, 10) -> (15, 10) straight line
    # (15, 10) -> (20, 15) with an arc fillet (90 deg arc with radius 5)
    # For a 90 deg counter-clockwise arc, bulge = tan(90 / 4) = tan(22.5 deg) = sqrt(2) - 1 ~= 0.41421356
    bulge_90 = math.tan(math.radians(90.0) / 4.0)

    # Note: ezdxf format='xyb' accepts (x, y, bulge)
    points = [
        (0.0, 10.0, 0.0),
        (15.0, 10.0, -bulge_90),  # Arc from (15, 10) to (20, 15)
        (20.0, 15.0, 0.0),
        (35.0, 15.0, 0.0),
    ]

    msp.add_lwpolyline(points)

    dxf_file = tmp_path / "stepped_fillet.dxf"
    doc.saveas(str(dxf_file))

    importer = DXFImporter(chordal_tolerance_mm=0.005)
    contour = importer.load_contour(dxf_file, axis_mapping="x_to_z")

    assert contour is not None
    assert len(contour.points) > 4  # The bulge arc should be expanded into multiple points
    # Front face re-zeroed to 0.0
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    # Length along Z is 35mm, so z_min should be -35mm
    assert pytest.approx(contour.z_min, abs=0.1) == -35.0
    # Radii should match 10mm and 15mm
    assert pytest.approx(contour.x_min, abs=0.1) == 10.0
    assert pytest.approx(contour.x_max, abs=0.1) == 15.0


def test_dxf_discrete_unordered_lines_and_arcs(tmp_path: Path) -> None:
    # Create DXF with separate LINE and ARC entities in scrambled order
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Entities forming a shaft from X=0 to 30:
    # Seg 1: (0, 12) -> (10, 12)
    # Seg 2: (10, 12) -> (10, 18)
    # Seg 3: (10, 18) -> (30, 18)
    # Add in reverse order
    msp.add_line((10.0, 18.0), (30.0, 18.0))
    msp.add_line((0.0, 12.0), (10.0, 12.0))
    msp.add_line((10.0, 12.0), (10.0, 18.0))

    dxf_file = tmp_path / "unordered_shaft.dxf"
    doc.saveas(str(dxf_file))

    importer = DXFImporter()
    contour = importer.load_contour(dxf_file)

    assert contour is not None
    assert pytest.approx(contour.z_max, abs=1e-3) == 0.0
    assert pytest.approx(contour.z_min, abs=0.1) == -30.0
    assert pytest.approx(contour.x_min, abs=0.1) == 12.0
    assert pytest.approx(contour.x_max, abs=0.1) == 18.0


def test_dxf_to_cam_pipeline_integration(tmp_path: Path) -> None:
    # End-to-end test: DXF import -> Roughing -> Finishing -> Post-processing
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    msp.add_line((0.0, 8.0), (12.0, 8.0))
    msp.add_line((12.0, 8.0), (12.0, 14.0))
    msp.add_line((12.0, 14.0), (25.0, 14.0))

    dxf_file = tmp_path / "part_for_cam.dxf"
    doc.saveas(str(dxf_file))

    importer = DXFImporter()
    contour = importer.load_contour(dxf_file)

    stock = Stock(od_mm=32.0, z_start_mm=1.0, z_end_mm=-30.0)
    tool = LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8)

    # 1. Generate roughing toolpath directly from DXF contour
    rough_cmds = generate_roughing_toolpath(
        profile_pts=contour.points,
        stock=stock,
        tool=tool,
        doc_mm=2.0,
        finish_allowance_mm=0.5,
    )
    assert len(rough_cmds) > 0
    assert any(c.mode == "G1" for c in rough_cmds)

    # 2. Generate finishing toolpath directly from DXF contour
    finish_cmds = generate_finishing_toolpath(
        profile_pts=contour.points,
        stock=stock,
        tool=tool,
        comp_mode=CompensationMode.COMPUTER,
    )
    assert len(finish_cmds) > 0
    assert any(c.mode == "G1" for c in finish_cmds)
