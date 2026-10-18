from __future__ import annotations

from lathecam.cam.finishing import CompensationMode
from lathecam.models.project import LatheProject, OperationType


def test_demo_project_workflow_and_recalculation() -> None:
    proj = LatheProject.create_demo_project()

    assert len(proj.operations) == 6
    assert proj.simulation_result is not None
    assert not proj.simulation_result.is_gouged
    assert "G18 G21 G40 G49 G80 G90 G95 G7" in proj.gcode_text
    assert "G76" in proj.gcode_text
    assert "G83" in proj.gcode_text

    # Modify roughing DOC dynamically and recalculate
    rough_op = next(o for o in proj.operations if o.op_type == OperationType.ROUGHING)
    initial_cmd_count = len(rough_op.commands)
    rough_op.doc_mm = 1.0  # Finer DOC -> more passes
    proj.recalculate_all()
    assert len(rough_op.commands) > initial_cmd_count

    # Switch finishing to controller compensation (G42 / G40)
    finish_op = next(o for o in proj.operations if o.op_type == OperationType.FINISHING)
    finish_op.comp_mode = CompensationMode.CONTROLLER
    proj.recalculate_all()
    assert "G42" in proj.gcode_text
    assert "G40" in proj.gcode_text


def test_project_lcam_save_load(tmp_path) -> None:
    proj = LatheProject.create_demo_project()
    proj.post_dialect = "fanuc"
    proj.recalculate_all()
    assert "G50 S" in proj.gcode_text

    lcam_file = tmp_path / "shaft_demo.lcam"
    proj.save_to_file(lcam_file)
    assert lcam_file.exists()

    loaded = LatheProject.load_from_file(lcam_file)
    assert loaded.name == proj.name
    assert loaded.post_dialect == "fanuc"
    assert len(loaded.operations) == len(proj.operations)
    assert len(loaded.contour.points) == len(proj.contour.points)
    assert "G50 S" in loaded.gcode_text


def test_i18n_french_and_light_theme() -> None:
    from lathecam.ui.i18n import get_language, set_language, tr
    from lathecam.ui.theme import get_viewport_colors

    set_language("fr")
    assert get_language() == "fr"
    assert "Arbre FeatureManager" in tr("tree.dock_title")
    assert "Inspecteur de Propriétés" in tr("props.dock_title")
    assert "Thème Clair" in tr("toolbar.theme_light")

    set_language("en")
    assert get_language() == "en"
    assert "FeatureManager Tree" in tr("tree.dock_title")

    light_colors = get_viewport_colors("light")
    dark_colors = get_viewport_colors("dark")
    assert light_colors["bg_bottom"] == "#f8fafc"
    assert light_colors["profile_line"] == "#0f172a"
    assert dark_colors["profile_line"] == "#f8fafc"


