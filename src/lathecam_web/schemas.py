"""Pydantic v2 Schemas for LatheCAM Web REST API."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class StockSchema(BaseModel):
    od_mm: float = 40.0
    id_mm: float = 0.0
    z_start_mm: float = 2.0
    z_end_mm: float = -46.0


class FaceSchema(BaseModel):
    face_id: str
    index: int
    face_type: str
    z_min: float
    z_max: float
    dia_min_mm: float
    dia_max_mm: float
    length_mm: float
    points: list[list[float]] = Field(default_factory=list)


class ToolSchema(BaseModel):
    tool_id: int
    name: str
    insert_shape: str = "C"
    inscribed_circle_mm: float = 12.7
    thickness_mm: float = 4.76
    nose_radius_mm: float = 0.8
    cutting_edge_length_mm: float = 12.0
    clearance_angle_deg: float = 5.0
    lead_angle_deg: float = 95.0
    orientation: int = 3
    max_doc_mm: float = 2.0
    tip_width_mm: float = 3.0
    hand: str = "R"


class MotionCmdSchema(BaseModel):
    mode: str
    x: float | None = None
    z: float | None = None
    i: float | None = None
    k: float | None = None
    f: float | None = None
    raw_params: dict[str, Any] | None = None


class OperationSchema(BaseModel):
    op_id: str
    name: str
    op_type: str
    tool_id: int = 1
    enabled: bool = True
    geometry_scope: str = "all"
    assigned_face_id: str | None = None
    bound_z_start_mm: float | None = None
    bound_z_end_mm: float | None = None
    css_m_min: float = 180.0
    max_rpm: int = 2500
    rpm: int = 1000
    feed_mm_rev: float = 0.20
    doc_mm: float = 1.8
    finish_allowance_mm: float = 0.4
    retract_mm: float = 0.8
    comp_mode: str = "COMPUTER"
    stepover_z_mm: float = 1.0
    pitch_mm: float = 1.5
    major_dia_mm: float = 16.0
    thread_z_start_mm: float = 0.0
    thread_z_end_mm: float = -11.0
    target_z_mm: float = -42.0
    target_x_radius_mm: float = 0.0
    peck_depth_mm: float = 2.0
    warning_message: str | None = None
    command_count: int = 0
    commands: list[MotionCmdSchema] = Field(default_factory=list)


class VerificationReportSchema(BaseModel):
    is_valid: bool = True
    total_lines: int = 0
    rapid_count: int = 0
    linear_count: int = 0
    arc_count: int = 0
    cycle_count: int = 0
    max_arc_radius_error_mm: float = 0.0
    max_part_gouge_mm: float = 0.0
    bounding_box: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    error_count: int = 0
    warning_count: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)


class ProjectStateSchema(BaseModel):
    name: str
    stock: StockSchema
    contour_points: list[list[float]]
    faces: list[FaceSchema] = Field(default_factory=list)
    operations: list[OperationSchema] = Field(default_factory=list)
    tools: list[ToolSchema] = Field(default_factory=list)
    is_diameter_mode: bool = True
    post_dialect: str = "linuxcnc"
    gcode_text: str = ""
    verification: VerificationReportSchema | None = None


class RecalculateRequest(BaseModel):
    name: str | None = None
    stock: StockSchema | None = None
    operations: list[OperationSchema] | None = None
    tools: list[ToolSchema] | None = None
    is_diameter_mode: bool | None = None
    post_dialect: str | None = None


class AddFaceOpRequest(BaseModel):
    face_id: str
    op_type: str  # "OD Roughing", "OD Profile Finishing", "Facing", "OD Threading (G76)", "Peck Parting / Grooving", "Axial Peck Drilling (G83)"


class SimulationWaypoint(BaseModel):
    step_index: int
    op_index: int
    op_name: str
    mode: str
    z: float
    x: float
    x_dia: float
    i: float | None = None
    k: float | None = None
    f: float | None = None
    tool_id: int
    comment: str | None = None
