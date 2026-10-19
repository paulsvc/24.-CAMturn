from __future__ import annotations

from pathlib import Path

from lathecam.models.project import LatheProject, OperationType
from lathecam.post.verifier import verify_gcode


def test_all_project_dialects_pass_automated_verification() -> None:
    """Verifies that LinuxCNC, Fanuc, and NCViewer dialects produce 100% error-free,
    gouge-free, and warning-free G-code with sub-micron arc center accuracy.
    """
    for dialect in ("linuxcnc", "fanuc", "ncviewer"):
        proj = LatheProject.create_demo_project()
        proj.post_dialect = dialect
        proj.recalculate_all()

        report = proj.verification_report
        assert report is not None
        assert report.is_valid, f"Dialect {dialect} failed verification:\n{report.summary()}"
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.max_arc_radius_error_mm < 0.001
        assert report.max_part_gouge_mm == 0.0


def test_published_gcode_folder_files_are_valid() -> None:
    """Verifies all published sample G-code files in the `gcode/` directory."""
    proj = LatheProject.create_demo_project()
    gcode_dir = Path(__file__).resolve().parent.parent / "gcode"

    expected_files = [
        "stepped_shaft_ncviewer.nc",
        "stepped_shaft_linuxcnc.ngc",
        "stepped_shaft_fanuc.nc",
        "stepped_shaft_face_bounded.ngc",
    ]
    for fname in expected_files:
        fpath = gcode_dir / fname
        assert fpath.exists(), f"Published G-code file missing: {fpath}"
        content = fpath.read_text(encoding="utf-8")
        report = verify_gcode(content, stock=proj.stock, part_polygon=proj.part_polygon)
        assert report.is_valid, f"{fname} failed verification:\n{report.summary()}"
        assert report.error_count == 0


def test_verifier_catches_runaway_arcs_and_diagonal_rapids() -> None:
    """Ensures the automated verifier catches bogus runaway arcs, radius mismatches,
    and diagonal rapid collisions inside the stock envelope.
    """
    proj = LatheProject.create_demo_project()

    bad_gcode = """%
(BAD GCODE TEST)
G18 G21 G40 G80 G90 G95 G7
T1 M6 G43
G96 D2500 S200 M3
G0 X0.000 Z2.000
G0 X40.000 Z-40.000
G1 X16.955 Z-13.750 F0.120
G3 X24.942 Z-20.250 I-958.982 K-594.467 F0.120
G2 X30.000 Z-25.000 I5.000 K0.000 F0.120
M5
M30
%
"""
    report = verify_gcode(bad_gcode, stock=proj.stock, part_polygon=proj.part_polygon)
    assert not report.is_valid
    error_codes = {issue.code for issue in report.issues if issue.severity == "ERROR"}
    assert "RAPID_DIAGONAL_IN_STOCK" in error_codes
    assert "RAPID_PART_COLLISION" in error_codes
    assert "ARC_RUNAWAY_RADIUS" in error_codes
    assert "ARC_RADIUS_MISMATCH" in error_codes
