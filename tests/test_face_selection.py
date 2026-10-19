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
