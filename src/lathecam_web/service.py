"""Backend Service Layer for LatheCAM Web API.

Encapsulates LatheProject state, CAD file ingestion, CAM recalculation,
3D mesh generation, and simulation trajectory waypoints.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile
from typing import Any

from lathecam.cad.contour import Contour
from lathecam.cad.face import FaceType, TurnedFace
from lathecam.cad.geometry import Point2D
from lathecam.cam.commands import MotionCmd
from lathecam.cam.finishing import CompensationMode
from lathecam.cam.tools import (
    ISO_SHAPE_DESCRIPTIONS,
    LatheTool,
    ToolOrientation,
)
from lathecam.models.project import LatheProject, OperationNode, OperationType
from lathecam.models.stock import Stock
from lathecam.post.fanuc import FanucPostProcessor
from lathecam.post.linuxcnc import LinuxCNCPostProcessor
from lathecam.post.ncviewer import NCViewerPostProcessor
from lathecam.post.verifier import verify_gcode

from lathecam_web.mesh import generate_revolved_mesh, generate_stock_mesh
from lathecam_web.schemas import (
    FaceSchema,
    MotionCmdSchema,
    OperationSchema,
    ProjectStateSchema,
    SimulationWaypoint,
    StockSchema,
    ToolSchema,
    VerificationReportSchema,
)


class LatheWebService:
    """Singleton service managing the active project and web operations."""

    def __init__(self) -> None:
        self.project: LatheProject = LatheProject.create_demo_project()

    def get_state(self) -> ProjectStateSchema:
        """Serializes current project into a Pydantic state model."""
        stock_schema = StockSchema(
            od_mm=self.project.stock.od_mm,
            id_mm=self.project.stock.id_mm,
            z_start_mm=self.project.stock.z_start_mm,
            z_end_mm=self.project.stock.z_end_mm,
        )

        faces_schema = [
            FaceSchema(
                face_id=f.face_id,
                index=f.index,
                face_type=f.face_type.value,
                z_min=round(f.z_min, 3),
                z_max=round(f.z_max, 3),
                dia_min_mm=round(f.x_min * 2.0, 2),
                dia_max_mm=round(f.dia_max_mm, 2),
                length_mm=round(f.axial_length_mm, 2),
                points=[[round(p[0], 3), round(p[1], 3)] for p in f.points],
            )
            for f in self.project.faces
        ]

        ops_schema: list[OperationSchema] = []
        for op in self.project.operations:
            cmds_schema = [
                MotionCmdSchema(
                    mode=cmd.mode,
                    x=round(cmd.x, 4) if cmd.x is not None else None,
                    z=round(cmd.z, 4) if cmd.z is not None else None,
                    i=round(cmd.i, 4) if cmd.i is not None else None,
                    k=round(cmd.k, 4) if cmd.k is not None else None,
                    f=round(cmd.f, 4) if cmd.f is not None else None,
                    raw_params=cmd.raw_params,
                )
                for cmd in op.commands
            ]

            ops_schema.append(
                OperationSchema(
                    op_id=op.op_id,
                    name=op.name,
                    op_type=op.op_type.value,
                    tool_id=op.tool_id,
                    enabled=op.enabled,
                    geometry_scope=op.geometry_scope,
                    assigned_face_id=op.assigned_face_id,
                    bound_z_start_mm=op.bound_z_start_mm,
                    bound_z_end_mm=op.bound_z_end_mm,
                    css_m_min=op.css_m_min,
                    max_rpm=op.max_rpm,
                    rpm=op.rpm,
                    feed_mm_rev=op.feed_mm_rev,
                    doc_mm=op.doc_mm,
                    finish_allowance_mm=op.finish_allowance_mm,
                    retract_mm=op.retract_mm,
                    comp_mode=op.comp_mode.name,
                    stepover_z_mm=op.stepover_z_mm,
                    pitch_mm=op.pitch_mm,
                    major_dia_mm=op.major_dia_mm,
                    thread_z_start_mm=op.thread_z_start_mm,
                    thread_z_end_mm=op.thread_z_end_mm,
                    target_z_mm=op.target_z_mm,
                    target_x_radius_mm=op.target_x_radius_mm,
                    peck_depth_mm=op.peck_depth_mm,
                    warning_message=op.warning_message,
                    command_count=len(op.commands),
                    commands=cmds_schema,
                )
            )

        tools_schema = [
            ToolSchema(
                tool_id=t.tool_id,
                name=t.name,
                insert_shape=t.insert_shape,
                inscribed_circle_mm=t.inscribed_circle_mm,
                thickness_mm=t.thickness_mm,
                nose_radius_mm=t.nose_radius_mm,
                cutting_edge_length_mm=t.cutting_edge_length_mm,
                clearance_angle_deg=t.clearance_angle_deg,
                lead_angle_deg=t.lead_angle_deg,
                orientation=t.orientation.value,
                max_doc_mm=t.max_doc_mm,
                tip_width_mm=t.tip_width_mm,
                hand=t.hand,
            )
            for t in self.project.tools.values()
        ]

        verif_schema: VerificationReportSchema | None = None
        if self.project.verification_report:
            vr = self.project.verification_report
            verif_schema = VerificationReportSchema(
                is_valid=vr.is_valid,
                total_lines=vr.total_lines,
                rapid_count=vr.rapid_count,
                linear_count=vr.linear_count,
                arc_count=vr.arc_count,
                cycle_count=vr.cycle_count,
                max_arc_radius_error_mm=round(vr.max_arc_radius_error_mm, 5),
                max_part_gouge_mm=round(vr.max_part_gouge_mm, 4),
                bounding_box=[round(b, 3) for b in vr.bounding_box],
                error_count=vr.error_count,
                warning_count=vr.warning_count,
                issues=[
                    {
                        "line": i.line_number,
                        "code": i.code,
                        "severity": i.severity,
                        "message": i.message,
                        "raw_line": i.raw_line,
                    }
                    for i in vr.issues
                ],
            )

        return ProjectStateSchema(
            name=self.project.name,
            stock=stock_schema,
            contour_points=[[round(p[0], 4), round(p[1], 4)] for p in self.project.contour.points],
            faces=faces_schema,
            operations=ops_schema,
            tools=tools_schema,
            is_diameter_mode=self.project.is_diameter_mode,
            post_dialect=self.project.post_dialect,
            gcode_text=self.project.gcode_text,
            verification=verif_schema,
        )

    def load_demo(self) -> ProjectStateSchema:
        """Resets the project to the stepped aerospace demo shaft."""
        self.project = LatheProject.create_demo_project()
        return self.get_state()

    def update_project(
        self,
        name: str | None = None,
        stock: StockSchema | None = None,
        operations: list[OperationSchema] | None = None,
        tools: list[ToolSchema] | None = None,
        is_diameter_mode: bool | None = None,
        post_dialect: str | None = None,
    ) -> ProjectStateSchema:
        """Applies modifications and recalculates toolpaths."""
        if name is not None:
            self.project.name = name

        if is_diameter_mode is not None:
            self.project.is_diameter_mode = is_diameter_mode

        if post_dialect is not None:
            self.project.post_dialect = post_dialect

        if stock is not None:
            self.project.stock = Stock(
                od_mm=stock.od_mm,
                id_mm=stock.id_mm,
                z_start_mm=stock.z_start_mm,
                z_end_mm=stock.z_end_mm,
            )

        if tools is not None:
            updated_tools: dict[int, LatheTool] = {}
            for ts in tools:
                try:
                    orientation = ToolOrientation(ts.orientation)
                except Exception:
                    orientation = ToolOrientation.QUADRANT_3

                updated_tools[ts.tool_id] = LatheTool(
                    tool_id=ts.tool_id,
                    name=ts.name,
                    insert_shape=ts.insert_shape,
                    inscribed_circle_mm=ts.inscribed_circle_mm,
                    thickness_mm=ts.thickness_mm,
                    nose_radius_mm=ts.nose_radius_mm,
                    cutting_edge_length_mm=ts.cutting_edge_length_mm,
                    clearance_angle_deg=ts.clearance_angle_deg,
                    lead_angle_deg=ts.lead_angle_deg,
                    orientation=orientation,
                    max_doc_mm=ts.max_doc_mm,
                    tip_width_mm=ts.tip_width_mm,
                    hand=ts.hand,
                )
            self.project.tools = updated_tools

        if operations is not None:
            # Map type string to enum
            type_map = {op.value: op for op in OperationType}
            new_ops: list[OperationNode] = []
            for os_item in operations:
                op_enum = type_map.get(os_item.op_type, OperationType.ROUGHING)
                comp_mode = (
                    CompensationMode[os_item.comp_mode]
                    if os_item.comp_mode in CompensationMode.__members__
                    else CompensationMode.COMPUTER
                )

                new_ops.append(
                    OperationNode(
                        op_id=os_item.op_id,
                        name=os_item.name,
                        op_type=op_enum,
                        tool_id=os_item.tool_id,
                        enabled=os_item.enabled,
                        geometry_scope=os_item.geometry_scope,
                        assigned_face_id=os_item.assigned_face_id,
                        bound_z_start_mm=os_item.bound_z_start_mm,
                        bound_z_end_mm=os_item.bound_z_end_mm,
                        css_m_min=os_item.css_m_min,
                        max_rpm=os_item.max_rpm,
                        rpm=os_item.rpm,
                        feed_mm_rev=os_item.feed_mm_rev,
                        doc_mm=os_item.doc_mm,
                        finish_allowance_mm=os_item.finish_allowance_mm,
                        retract_mm=os_item.retract_mm,
                        comp_mode=comp_mode,
                        stepover_z_mm=os_item.stepover_z_mm,
                        pitch_mm=os_item.pitch_mm,
                        major_dia_mm=os_item.major_dia_mm,
                        thread_z_start_mm=os_item.thread_z_start_mm,
                        thread_z_end_mm=os_item.thread_z_end_mm,
                        target_z_mm=os_item.target_z_mm,
                        target_x_radius_mm=os_item.target_x_radius_mm,
                        peck_depth_mm=os_item.peck_depth_mm,
                    )
                )
            self.project.operations = new_ops

        # Trigger full recalculation
        self.project.recalculate_all()
        return self.get_state()

    def add_face_operation(self, face_id: str, op_type_str: str) -> ProjectStateSchema:
        """Creates and appends an operation targeted at a specific face."""
        face = self.project.get_face_by_id(face_id)
        if not face:
            raise ValueError(f"Face '{face_id}' not found")

        type_map = {op.value: op for op in OperationType}
        op_enum = type_map.get(op_type_str, OperationType.ROUGHING)

        self.project.create_operation_for_face(face, op_enum)
        self.project.recalculate_all()
        return self.get_state()

    def import_cad_file(self, filename: str, content_bytes: bytes) -> ProjectStateSchema:
        """Parses STEP or DXF, resets existing operations, and creates new stock."""
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content_bytes)
            tmp_path = Path(tmp.name)

        try:
            if suffix in (".step", ".stp"):
                from lathecam.cad.step_importer import STEPImporter
                importer = STEPImporter()
                contour = importer.extract_contour(tmp_path)
            elif suffix == ".dxf":
                from lathecam.cad.dxf_importer import DXFImporter
                importer = DXFImporter()
                contour = importer.import_file(tmp_path)
            else:
                raise ValueError(f"Unsupported CAD file extension: {suffix}")

            # Auto calculate stock bounds
            zs = [p[0] for p in contour.points]
            xs = [p[1] for p in contour.points]
            z_min = min(zs) if zs else -50.0
            z_max = max(zs) if zs else 0.0
            x_max = max(xs) if xs else 20.0

            # 2mm face margin, 4mm OD clearance
            stock_od = math.ceil((x_max * 2.0 + 4.0) / 5.0) * 5.0
            stock_z_start = math.ceil(z_max + 1.0)
            stock_z_end = math.floor(z_min - 5.0)

            stock = Stock(
                od_mm=float(stock_od),
                z_start_mm=float(stock_z_start),
                z_end_mm=float(stock_z_end),
                id_mm=0.0,
            )

            # Build project and reset operations (as required)
            self.project = LatheProject(
                name=Path(filename).stem,
                stock=stock,
                contour=contour,
                tools=LatheProject.default_tool_turret(),
                operations=[],  # Clean operations slate
            )
            self.project.recalculate_all()
            return self.get_state()

        finally:
            if tmp_path.exists():
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def get_mesh_part(self, cutaway: bool = True) -> dict[str, Any]:
        """Generates 3/4 cutaway revolved 3D workpiece mesh."""
        return generate_revolved_mesh(
            self.project.contour.points,
            num_slices=48,
            cutaway=cutaway,
            cutaway_angle_deg=90.0,
        )

    def get_mesh_stock(self) -> dict[str, Any]:
        """Generates cylindrical stock envelope mesh."""
        return generate_stock_mesh(
            od_mm=self.project.stock.od_mm,
            z_start_mm=self.project.stock.z_start_mm,
            z_end_mm=self.project.stock.z_end_mm,
            id_mm=self.project.stock.id_mm,
            num_slices=36,
        )

    def get_simulation_waypoints(self) -> list[SimulationWaypoint]:
        """Extracts linear and arc-interpolated toolpath waypoints for 60-120 FPS playback."""
        waypoints: list[SimulationWaypoint] = []
        step_idx = 0
        curr_z = self.project.stock.z_start_mm + 5.0
        curr_x = self.project.stock.od_mm / 2.0 + 5.0

        for op_idx, op in enumerate(self.project.operations):
            if not op.enabled:
                continue

            # Use preview commands (which unrolls G76 threading and G83 drilling)
            cmds = op.preview_commands if op.preview_commands else op.commands

            for cmd in cmds:
                mode = cmd.mode.upper()
                tool_id = op.tool_id

                if mode == "COMMENT":
                    comment_text = cmd.raw_params.get("comment", "") if cmd.raw_params else ""
                    waypoints.append(
                        SimulationWaypoint(
                            step_index=step_idx,
                            op_index=op_idx,
                            op_name=op.name,
                            mode="COMMENT",
                            z=round(curr_z, 4),
                            x=round(curr_x, 4),
                            x_dia=round(curr_x * 2.0, 4),
                            tool_id=tool_id,
                            comment=comment_text,
                        )
                    )
                    step_idx += 1
                    continue

                if mode in ("G0", "G1"):
                    target_z = cmd.z if cmd.z is not None else curr_z
                    target_x = cmd.x if cmd.x is not None else curr_x
                    curr_z = target_z
                    curr_x = target_x

                    waypoints.append(
                        SimulationWaypoint(
                            step_index=step_idx,
                            op_index=op_idx,
                            op_name=op.name,
                            mode=mode,
                            z=round(target_z, 4),
                            x=round(target_x, 4),
                            x_dia=round(target_x * 2.0, 4),
                            f=cmd.f if cmd.f is not None else op.feed_mm_rev,
                            tool_id=tool_id,
                        )
                    )
                    step_idx += 1

                elif mode in ("G2", "G3"):
                    # Discretize arc
                    target_z = cmd.z if cmd.z is not None else curr_z
                    target_x = cmd.x if cmd.x is not None else curr_x
                    i_val = cmd.i if cmd.i is not None else 0.0
                    k_val = cmd.k if cmd.k is not None else 0.0

                    # Arc center: (center_z, center_x) = (start_z + k, start_x + i)
                    c_z = curr_z + k_val
                    c_x = curr_x + i_val
                    radius = math.hypot(curr_z - c_z, curr_x - c_x)

                    start_ang = math.atan2(curr_x - c_x, curr_z - c_z)
                    end_ang = math.atan2(target_x - c_x, target_z - c_z)

                    if mode == "G2":  # Clockwise in Z-X plane
                        if end_ang >= start_ang:
                            end_ang -= 2.0 * math.pi
                    else:  # Counter-clockwise (G3)
                        if end_ang <= start_ang:
                            end_ang += 2.0 * math.pi

                    arc_steps = 10
                    for s in range(1, arc_steps + 1):
                        frac = s / arc_steps
                        ang = start_ang + frac * (end_ang - start_ang)
                        pt_z = c_z + radius * math.cos(ang)
                        pt_x = c_x + radius * math.sin(ang)

                        waypoints.append(
                            SimulationWaypoint(
                                step_index=step_idx,
                                op_index=op_idx,
                                op_name=op.name,
                                mode=mode,
                                z=round(pt_z, 4),
                                x=round(pt_x, 4),
                                x_dia=round(pt_x * 2.0, 4),
                                i=round(i_val, 4),
                                k=round(k_val, 4),
                                f=cmd.f if cmd.f is not None else op.feed_mm_rev,
                                tool_id=tool_id,
                            )
                        )
                        step_idx += 1

                    curr_z = target_z
                    curr_x = target_x

        return waypoints


# Global service instance
web_service = LatheWebService()
