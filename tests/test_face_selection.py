from __future__ import annotations

from lathecam.cad.face import FaceType, decompose_contour_into_faces
from lathecam.models.project import LatheProject, OperationType


def test_decompose_demo_shaft_into_faces() -> None:
    proj = LatheProject.create_demo_project()
    faces = decompose_contour_into_faces(proj.contour)

    assert len(faces) >= 8
    face_types = {f.face_type for f in faces}
    assert FaceType.CYLINDER in face_types
    assert FaceType.TAPER in face_types
    assert FaceType.FILLET in face_types
    assert FaceType.SHOULDER in face_types
    assert FaceType.GROOVE in face_types


def test_point_picking_resolves_correct_face() -> None:
    proj = LatheProject.create_demo_project()
    # Point near bearing seat cylinder (Z=-25.0, R=12.5 -> Ø25mm)
    best_face = min(proj.faces, key=lambda f: f.distance_to_point(-25.0, 12.5))
    assert best_face.face_type == FaceType.CYLINDER
    assert abs(best_face.dia_max_mm - 25.0) < 0.2
    assert abs(best_face.z_max - (-20.0)) < 0.2
    assert abs(best_face.z_min - (-30.0)) < 0.2


def test_face_bounded_roughing_and_finishing(tmp_path) -> None:
    proj = LatheProject.create_demo_project()
    # Find the Ø25mm bearing seat cylinder (Z=-20.0 to Z=-30.0)
    bearing_face = min(proj.faces, key=lambda f: f.distance_to_point(-25.0, 12.5))

    rough_op = proj.create_operation_for_face(bearing_face, OperationType.ROUGHING)
    finish_op = proj.create_operation_for_face(bearing_face, OperationType.FINISHING)
    proj.recalculate_all()

    assert rough_op.geometry_scope == "face"
    assert rough_op.assigned_face_id == bearing_face.face_id

    # Verify all linear cutting moves (G1) in rough_op stay within [-30.0 - tol, -20.0 + clearance]
    g1_z = [cmd.z for cmd in rough_op.commands if cmd.mode == "G1" and cmd.z is not None]
    assert len(g1_z) > 0
    assert min(g1_z) >= -30.5
    assert max(g1_z) <= -18.0  # Never cuts the front M16 thread journal at Z=0..-11.5!

    # Verify finishing pass on single face
    fin_z = [cmd.z for cmd in finish_op.commands if cmd.mode in ("G1", "G2", "G3") and cmd.z is not None]
    assert len(fin_z) > 0
    assert min(fin_z) >= -32.0
    assert max(fin_z) <= -17.0

    # Verify .lcam serialization preserves face scope
    lcam_path = tmp_path / "face_test.lcam"
    proj.save_to_file(lcam_path)
    loaded = LatheProject.load_from_file(lcam_path)
    loaded_rough = next(o for o in loaded.operations if o.op_id == rough_op.op_id)
    assert loaded_rough.geometry_scope == "face"
    assert loaded_rough.assigned_face_id == bearing_face.face_id
    assert loaded_rough.bound_z_start_mm == rough_op.bound_z_start_mm
    assert loaded_rough.bound_z_end_mm == rough_op.bound_z_end_mm


def test_face_bounded_finishing_on_vertical_shoulder() -> None:
    """Verify OD finish on a pure vertical shoulder face (e.g., F1 in Part1.STEP) works without error."""
    from pathlib import Path
    from lathecam.cad.step_importer import STEPImporter
    from lathecam.cam.finishing import offset_profile_pyclipper
    from lathecam.cam.shadowing import extract_upper_profile
    import shapely.geometry

    step_path = Path("step/Part1.STEP")
    if not step_path.exists():
        return

    importer = STEPImporter()
    shape = importer.load_shape(step_path)
    contour = importer.extract_contour(shape)
    proj = LatheProject(name="Part1 Shoulder Test", stock=proj_stock_for_contour(contour), contour=contour)

    # Locate the shoulder face at Z=0.0
    shoulder_face = next(f for f in proj.faces if f.face_type == FaceType.SHOULDER and abs(f.z_max) < 1e-3)
    assert shoulder_face is not None

    # Test direct offset on vertical shoulder points
    offset_pts = offset_profile_pyclipper(shoulder_face.points, offset_mm=0.4)
    assert len(offset_pts) == len(shoulder_face.points)

    # Test extract_upper_profile on LineString does not raise attribute error
    test_line = shapely.geometry.LineString([(0.0, 70.0), (0.0, 40.0)])
    extracted = extract_upper_profile(test_line)
    assert len(extracted) >= 1

    # Create finishing operation for F1 shoulder
    finish_op = proj.create_operation_for_face(shoulder_face, OperationType.FINISHING)
    proj.operations.append(finish_op)
    proj.recalculate_all()

    assert finish_op.warning_message is None
    assert len(finish_op.commands) > 0

    # Ensure cutting moves lie on the shoulder face (Z=0.0)
    g1_moves = [cmd for cmd in finish_op.commands if cmd.mode == "G1" and cmd.z is not None]
    assert len(g1_moves) >= 2
    # The shoulder face cut must be at Z=0.0
    face_cut = [cmd for cmd in g1_moves if abs(cmd.z) < 1e-3]
    assert len(face_cut) >= 1
    assert face_cut[0].x is not None


def proj_stock_for_contour(contour):
    from lathecam.models.stock import Stock
    return Stock(od_mm=contour.x_max * 2.0 + 4.0, z_start_mm=contour.z_max + 2.0, z_end_mm=contour.z_min - 5.0)
