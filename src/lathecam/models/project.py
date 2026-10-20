from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any
import shapely.geometry

from lathecam.cad.contour import Contour
from lathecam.cad.face import FaceType, TurnedFace, decompose_contour_into_faces
from lathecam.cad.geometry import Point2D
from lathecam.cam.commands import MotionCmd
from lathecam.cam.finishing import CompensationMode, generate_finishing_toolpath
from lathecam.cam.operations import DrillingOp, FacingOp, PartingOp, ThreadingOp
from lathecam.cam.roughing import generate_roughing_toolpath
from lathecam.cam.shadowing import compute_shadowed_polygon, profile_to_polygon
from lathecam.cam.simulator import SimulationResult, simulate_2d_material_removal
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock
from lathecam.post.fanuc import FanucPostProcessor
from lathecam.post.linuxcnc import LinuxCNCPostProcessor
from lathecam.post.ncviewer import NCViewerPostProcessor
from lathecam.post.verifier import VerificationReport, verify_gcode


class OperationType(Enum):
    FACING = "Facing"
    ROUGHING = "OD Roughing"
    FINISHING = "OD Profile Finishing"
    THREADING = "OD Threading (G76)"
    DRILLING = "Axial Peck Drilling (G83)"
    PARTING = "Peck Parting / Grooving"


@dataclass
class OperationNode:
    """Represents a configurable CAM operation in the FeatureManager tree."""
    op_id: str
    name: str
    op_type: OperationType
    tool_id: int = 1
    enabled: bool = True

    # Geometry Scope & Face Selection
    geometry_scope: str = "all"  # "all" or "face"
    assigned_face_id: str | None = None
    bound_z_start_mm: float | None = None
    bound_z_end_mm: float | None = None

    # Feeds & Speeds
    css_m_min: float = 180.0
    max_rpm: int = 2500
    rpm: int = 1000
    feed_mm_rev: float = 0.20

    # Geometry & Cut Parameters
    doc_mm: float = 1.8
    finish_allowance_mm: float = 0.4
    retract_mm: float = 0.8
    comp_mode: CompensationMode = CompensationMode.COMPUTER

    # Parametric Op Specifics
    stepover_z_mm: float = 1.0
    pitch_mm: float = 1.5
    major_dia_mm: float = 16.0
    thread_z_start_mm: float = 0.0
    thread_z_end_mm: float = -11.0
    target_z_mm: float = -42.0
    target_x_radius_mm: float = 0.0
    peck_depth_mm: float = 2.0

    # Calculated state
    commands: list[MotionCmd] = field(default_factory=list)
    preview_commands: list[MotionCmd] = field(default_factory=list)
    warning_message: str | None = None


@dataclass
class LatheProject:
    """Central application data model holding Stock, CAD Contour, Tool Turret, and CAM Operations."""
    name: str
    stock: Stock
    contour: Contour
    tools: dict[int, LatheTool] = field(default_factory=dict)
    operations: list[OperationNode] = field(default_factory=list)
    is_diameter_mode: bool = True
    post_dialect: str = "linuxcnc"  # 'linuxcnc', 'fanuc', or 'ncviewer'

    # Computed outputs
    faces: list[TurnedFace] = field(default_factory=list)
    part_polygon: shapely.geometry.Polygon | None = None
    shadowed_polygon: shapely.geometry.Polygon | None = None
    simulation_result: SimulationResult | None = None
    verification_report: VerificationReport | None = None
    gcode_text: str = ""

    def __post_init__(self) -> None:
        if not self.tools:
            self.tools = self.default_tool_turret()
        self.faces = decompose_contour_into_faces(self.contour)

    def get_face_by_id(self, face_id: str | None) -> TurnedFace | None:
        if not face_id:
            return None
        return next((f for f in self.faces if f.face_id == face_id), None)

    @staticmethod
    def default_tool_turret() -> dict[int, LatheTool]:
        return {
            1: LatheTool.cnmg_roughing(tool_id=1, nose_radius_mm=0.8),
            2: LatheTool.dnmg_finishing(tool_id=2, nose_radius_mm=0.4),
            3: LatheTool.vnmg_profiling(tool_id=3, nose_radius_mm=0.4),
            4: LatheTool.parting_blade(tool_id=4, width_mm=3.0),
            5: LatheTool.threading_tool(tool_id=5),
            6: LatheTool.center_drill(tool_id=6, diameter_mm=6.0),
        }

    @classmethod
    def create_demo_project(cls) -> LatheProject:
        """Creates a rich stepped aerospace/automotive turned shaft with central drilled hole, fillet, taper, undercut groove, and thread journal."""
        hole_r = 3.0   # Ø6mm axial hole drilled by Op 5
        hole_z = -22.0 # Drilled depth
        tip_z = -23.8  # Standard 118° drill point on centerline

        pts: list[Point2D] = [
            (0.0, 6.5),     # Front chamfer start
            (-1.5, 8.0),    # M16x1.5 thread journal (OD 16mm -> R=8.0mm)
            (-11.5, 8.0),
            (-11.5, 6.8),   # Thread relief undercut groove (R=6.8mm)
            (-13.5, 6.8),
            (-13.5, 8.5),   # Taper start
            (-20.0, 12.5),  # Taper end into bearing seat (OD 25mm -> R=12.5mm)
            (-30.0, 12.5),
        ]
        # Add a smooth 3.0mm radius concave fillet into the rear shoulder (R=12.5 -> R=15.5, Z=-30 -> Z=-33)
        fillet_center_z = -30.0
        fillet_center_x = 15.5
        fillet_r = 3.0
        for i in range(1, 9):
            theta = -math.pi / 2.0 - (i / 8.0) * (math.pi / 2.0)
            fz = fillet_center_z + fillet_r * math.cos(theta)
            fx = fillet_center_x + fillet_r * math.sin(theta)
            pts.append((fz, fx))

        pts.extend([
            (-33.0, 18.0),  # Rear flange shoulder (OD 36mm -> R=18.0mm)
            (-42.0, 18.0),  # End of flange OD
            (-42.0, 0.0),   # Rear face down to spindle centerline
            (tip_z, 0.0),   # Centerline forward to drill tip cone
            (hole_z, hole_r), # 118° drill point up to Ø6mm bore
            (0.0, hole_r),  # Axial hole bore forward to front face
            (0.0, 6.5),     # Front face up to chamfer start (watertight closed contour)
        ])

        contour = Contour(pts)
        stock = Stock(od_mm=40.0, z_start_mm=2.0, z_end_mm=-46.0, id_mm=0.0)

        ops = [
            OperationNode(
                op_id="op_face_1",
                name="1. Face Front Stock",
                op_type=OperationType.FACING,
                tool_id=1,
                css_m_min=180.0,
                max_rpm=2200,
                feed_mm_rev=0.20,
                stepover_z_mm=1.0,
            ),
            OperationNode(
                op_id="op_rough_1",
                name="2. OD Roughing (CNMG 80°)",
                op_type=OperationType.ROUGHING,
                tool_id=1,
                css_m_min=200.0,
                max_rpm=2500,
                feed_mm_rev=0.25,
                doc_mm=1.8,
                finish_allowance_mm=0.4,
                retract_mm=0.8,
            ),
            OperationNode(
                op_id="op_finish_1",
                name="3. OD Profile Finishing (DNMG 55°)",
                op_type=OperationType.FINISHING,
                tool_id=2,
                css_m_min=240.0,
                max_rpm=2800,
                feed_mm_rev=0.12,
                comp_mode=CompensationMode.COMPUTER,
                retract_mm=1.0,
            ),
            OperationNode(
                op_id="op_thread_1",
                name="4. M16x1.5 OD Threading (G76)",
                op_type=OperationType.THREADING,
                tool_id=5,
                rpm=800,
                pitch_mm=1.5,
                major_dia_mm=16.0,
                thread_z_start_mm=-1.0,
                thread_z_end_mm=-12.5,
            ),
            OperationNode(
                op_id="op_drill_1",
                name="5. Axial Peck Drilling Ø6mm (G83)",
                op_type=OperationType.DRILLING,
                tool_id=6,
                rpm=1200,
                feed_mm_rev=0.12,
                target_z_mm=-22.0,
                peck_depth_mm=4.0,
            ),
            OperationNode(
                op_id="op_part_1",
                name="6. Peck Part-Off (3mm Blade)",
                op_type=OperationType.PARTING,
                tool_id=4,
                css_m_min=110.0,
                max_rpm=1500,
                feed_mm_rev=0.06,
                target_z_mm=-42.0,
                target_x_radius_mm=0.0,
                peck_depth_mm=2.5,
            ),
        ]

        proj = cls(
            name="Stepped Threaded Drive Shaft",
            stock=stock,
            contour=contour,
            operations=ops,
        )
        proj.recalculate_all()
        return proj

    def create_operation_for_face(self, face: TurnedFace, op_type: OperationType) -> OperationNode:
        """Instantiates and appends a new OperationNode automatically bound to the given TurnedFace."""
        import uuid

        idx = len(self.operations) + 1
        default_tool = {
            OperationType.FACING: 1,
            OperationType.ROUGHING: 1,
            OperationType.FINISHING: 2,
            OperationType.PARTING: 4,
            OperationType.THREADING: 5,
            OperationType.DRILLING: 6,
        }.get(op_type, 1)

        op = OperationNode(
            op_id=f"op_{uuid.uuid4().hex[:6]}",
            name=f"{idx}. {op_type.value} [F{face.index} Ø{face.dia_max_mm:.1f}]",
            op_type=op_type,
            tool_id=default_tool,
            geometry_scope="face",
            assigned_face_id=face.face_id,
            bound_z_start_mm=round(face.z_max, 3),
            bound_z_end_mm=round(face.z_min, 3),
        )

        if op_type == OperationType.THREADING:
            op.major_dia_mm = round(face.dia_max_mm, 2)
            op.thread_z_start_mm = round(face.z_max, 2)
            op.thread_z_end_mm = round(face.z_min, 2)
        elif op_type == OperationType.PARTING:
            op.target_z_mm = round(face.z_min, 2)
            op.target_x_radius_mm = round(face.x_min if face.face_type == FaceType.GROOVE else 0.0, 2)

        self.operations.append(op)
        return op

    def recalculate_all(self) -> None:
        """Recalculates all CAM operation toolpaths, 2D material removal simulation, and LinuxCNC G-code."""
        self.faces = decompose_contour_into_faces(self.contour)

        try:
            self.part_polygon = profile_to_polygon(
                self.contour.points,
                z_min=self.stock.z_end_mm,
                z_max=0.0,
            )
        except Exception:
            self.part_polygon = None

        rough_tool = self.tools.get(1) or next(iter(self.tools.values()))
        try:
            self.shadowed_polygon = compute_shadowed_polygon(
                self.contour.points,
                rough_tool,
                z_min_bound=self.stock.z_end_mm,
                z_max_bound=0.0,
            )
        except Exception:
            self.shadowed_polygon = self.part_polygon

        all_post_cmds: list[MotionCmd] = []
        all_sim_cmds: list[MotionCmd] = []
        last_tool_id: int | None = None
        effective_z_start = self.stock.z_start_mm

        for op in self.operations:
            op.warning_message = None
            op.commands = []
            op.preview_commands = []

            if not op.enabled:
                continue

            tool = self.tools.get(op.tool_id)
            if tool is None:
                op.warning_message = f"Tool T{op.tool_id} not found in turret"
                continue

            try:
                header_cmds: list[MotionCmd] = []
                if op.tool_id != last_tool_id:
                    header_cmds.append(MotionCmd(mode="TOOL_CHANGE", raw_params={"tool_id": op.tool_id}))
                    last_tool_id = op.tool_id

                if op.op_type in (OperationType.FACING, OperationType.ROUGHING, OperationType.FINISHING, OperationType.PARTING):
                    header_cmds.append(
                        MotionCmd(
                            mode="SPINDLE_CSS",
                            raw_params={"max_rpm": op.max_rpm, "css_m_min": op.css_m_min},
                        )
                    )
                elif op.op_type != OperationType.DRILLING:
                    # Note: DrillingOp.generate() emits its own SPINDLE_RPM
                    header_cmds.append(
                        MotionCmd(
                            mode="SPINDLE_RPM",
                            raw_params={"rpm": op.rpm},
                        )
                    )

                use_face_bounds = op.geometry_scope == "face"
                z_s = op.bound_z_start_mm if use_face_bounds else None
                z_e = op.bound_z_end_mm if use_face_bounds else None
                target_face = self.get_face_by_id(op.assigned_face_id) if use_face_bounds else None

                match op.op_type:
                    case OperationType.FACING:
                        face_target_z = z_e if z_e is not None else 0.0
                        f_op = FacingOp(
                            stock=self.stock,
                            tool=tool,
                            target_z_mm=face_target_z,
                            stepover_z_mm=op.stepover_z_mm,
                            feed_mm_rev=op.feed_mm_rev,
                        )
                        op_cmds = f_op.generate()
                        op.commands = header_cmds + op_cmds
                        op.preview_commands = list(op.commands)
                        effective_z_start = min(effective_z_start, face_target_z)

                    case OperationType.ROUGHING:
                        rough_stock = Stock(
                            od_mm=self.stock.od_mm,
                            z_start_mm=effective_z_start,
                            z_end_mm=self.stock.z_end_mm,
                            id_mm=self.stock.id_mm,
                        )
                        op_cmds = generate_roughing_toolpath(
                            profile_pts=self.contour.points,
                            stock=rough_stock,
                            tool=tool,
                            doc_mm=op.doc_mm,
                            feed_mm_rev=op.feed_mm_rev,
                            finish_allowance_mm=op.finish_allowance_mm,
                            retract_mm=op.retract_mm,
                            z_start=z_s,
                            z_end=z_e,
                        )
                        op.commands = header_cmds + op_cmds
                        op.preview_commands = list(op.commands)

                    case OperationType.FINISHING:
                        op_cmds = generate_finishing_toolpath(
                            profile_pts=self.contour.points,
                            stock=self.stock,
                            tool=tool,
                            comp_mode=op.comp_mode,
                            feed_mm_rev=op.feed_mm_rev,
                            retract_mm=op.retract_mm,
                            z_start=z_s,
                            z_end=z_e,
                            target_face_pts=target_face.points if target_face is not None else None,
                        )
                        op.commands = header_cmds + op_cmds
                        op.preview_commands = list(op.commands)

                    case OperationType.THREADING:
                        t_op = ThreadingOp(
                            pitch_mm=op.pitch_mm,
                            major_dia_mm=op.major_dia_mm,
                            z_start_mm=op.thread_z_start_mm,
                            z_end_mm=op.thread_z_end_mm,
                        )
                        op.commands = header_cmds + t_op.generate()
                        op.preview_commands = header_cmds + t_op.generate_unrolled_g33_preview()

                    case OperationType.PARTING:
                        p_op = PartingOp(
                            stock=self.stock,
                            tool=tool,
                            target_z_mm=op.target_z_mm,
                            target_x_radius_mm=op.target_x_radius_mm,
                            peck_depth_mm=op.peck_depth_mm,
                            feed_mm_rev=op.feed_mm_rev,
                        )
                        op.commands = header_cmds + p_op.generate()
                        op.preview_commands = list(op.commands)

                    case OperationType.DRILLING:
                        d_op = DrillingOp(
                            z_depth_mm=op.target_z_mm,
                            peck_q_mm=op.peck_depth_mm,
                            feed_mm_rev=op.feed_mm_rev,
                            rpm=op.rpm,
                        )
                        op.commands = header_cmds + d_op.generate()
                        op.preview_commands = header_cmds + d_op.generate_unrolled_peck_preview()

                dialect = self.post_dialect.lower()
                if dialect == "ncviewer":
                    all_post_cmds.extend(op.preview_commands)
                else:
                    all_post_cmds.extend(op.commands)

                if op.op_type == OperationType.ROUGHING:
                    all_sim_cmds.extend(op.preview_commands)

            except Exception as exc:
                op.warning_message = str(exc)

        # Simulate 2D material removal
        if self.part_polygon is not None:
            try:
                self.simulation_result = simulate_2d_material_removal(
                    stock=self.stock,
                    target_part_poly=self.part_polygon,
                    commands=all_sim_cmds,
                    tool=rough_tool,
                )
            except Exception:
                self.simulation_result = None

        # Post-process G-code
        dialect = self.post_dialect.lower()
        if dialect == "fanuc":
            post = FanucPostProcessor(is_diameter_mode=self.is_diameter_mode)
        elif dialect == "ncviewer":
            post = NCViewerPostProcessor(is_diameter_mode=False, xz_arc_chirality=True)
        else:
            post = LinuxCNCPostProcessor(is_diameter_mode=self.is_diameter_mode)

        self.gcode_text = post.export(
            all_post_cmds,
            metadata={"program_name": f"LatheCAM - {self.name}"},
        )

        # Automatically verify generated G-code
        self.verification_report = verify_gcode(
            self.gcode_text,
            stock=self.stock,
            part_polygon=self.part_polygon,
        )

    def save_to_file(self, filepath: str | Path) -> Path:
        """Serializes the LatheProject state to a JSON .lcam project file."""
        path = Path(filepath)
        data: dict[str, Any] = {
            "version": "1.1",
            "name": self.name,
            "is_diameter_mode": self.is_diameter_mode,
            "post_dialect": self.post_dialect,
            "stock": {
                "od_mm": self.stock.od_mm,
                "id_mm": self.stock.id_mm,
                "z_start_mm": self.stock.z_start_mm,
                "z_end_mm": self.stock.z_end_mm,
            },
            "tools": [t.to_dict() for t in self.tools.values()],
            "contour_points": [[z, x] for z, x in self.contour.points],
            "operations": [
                {
                    "op_id": op.op_id,
                    "name": op.name,
                    "op_type": op.op_type.name,
                    "tool_id": op.tool_id,
                    "enabled": op.enabled,
                    "geometry_scope": op.geometry_scope,
                    "assigned_face_id": op.assigned_face_id,
                    "bound_z_start_mm": op.bound_z_start_mm,
                    "bound_z_end_mm": op.bound_z_end_mm,
                    "css_m_min": op.css_m_min,
                    "max_rpm": op.max_rpm,
                    "rpm": op.rpm,
                    "feed_mm_rev": op.feed_mm_rev,
                    "doc_mm": op.doc_mm,
                    "finish_allowance_mm": op.finish_allowance_mm,
                    "retract_mm": op.retract_mm,
                    "comp_mode": op.comp_mode.name,
                    "stepover_z_mm": op.stepover_z_mm,
                    "pitch_mm": op.pitch_mm,
                    "major_dia_mm": op.major_dia_mm,
                    "thread_z_start_mm": op.thread_z_start_mm,
                    "thread_z_end_mm": op.thread_z_end_mm,
                    "target_z_mm": op.target_z_mm,
                    "target_x_radius_mm": op.target_x_radius_mm,
                    "peck_depth_mm": op.peck_depth_mm,
                }
                for op in self.operations
            ],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load_from_file(cls, filepath: str | Path) -> LatheProject:
        """Deserializes a LatheProject from a JSON .lcam project file."""
        path = Path(filepath)
        data = json.loads(path.read_text(encoding="utf-8"))

        st_data = data["stock"]
        stock = Stock(
            od_mm=float(st_data["od_mm"]),
            id_mm=float(st_data.get("id_mm", 0.0)),
            z_start_mm=float(st_data.get("z_start_mm", 0.0)),
            z_end_mm=float(st_data["z_end_mm"]),
        )
        pts: list[Point2D] = [(float(p[0]), float(p[1])) for p in data["contour_points"]]
        contour = Contour(pts)

        ops: list[OperationNode] = []
        for od in data.get("operations", []):
            ops.append(
                OperationNode(
                    op_id=str(od["op_id"]),
                    name=str(od["name"]),
                    op_type=OperationType[od["op_type"]],
                    tool_id=int(od["tool_id"]),
                    enabled=bool(od.get("enabled", True)),
                    geometry_scope=str(od.get("geometry_scope", "all")),
                    assigned_face_id=od.get("assigned_face_id"),
                    bound_z_start_mm=float(od["bound_z_start_mm"]) if od.get("bound_z_start_mm") is not None else None,
                    bound_z_end_mm=float(od["bound_z_end_mm"]) if od.get("bound_z_end_mm") is not None else None,
                    css_m_min=float(od.get("css_m_min", 180.0)),
                    max_rpm=int(od.get("max_rpm", 2500)),
                    rpm=int(od.get("rpm", 1000)),
                    feed_mm_rev=float(od.get("feed_mm_rev", 0.20)),
                    doc_mm=float(od.get("doc_mm", 1.8)),
                    finish_allowance_mm=float(od.get("finish_allowance_mm", 0.4)),
                    retract_mm=float(od.get("retract_mm", 0.8)),
                    comp_mode=CompensationMode[od.get("comp_mode", "COMPUTER")],
                    stepover_z_mm=float(od.get("stepover_z_mm", 1.0)),
                    pitch_mm=float(od.get("pitch_mm", 1.5)),
                    major_dia_mm=float(od.get("major_dia_mm", 16.0)),
                    thread_z_start_mm=float(od.get("thread_z_start_mm", 0.0)),
                    thread_z_end_mm=float(od.get("thread_z_end_mm", -11.0)),
                    target_z_mm=float(od.get("target_z_mm", -42.0)),
                    target_x_radius_mm=float(od.get("target_x_radius_mm", 0.0)),
                    peck_depth_mm=float(od.get("peck_depth_mm", 2.0)),
                )
            )

        tools_dict: dict[int, LatheTool] = {}
        for td in data.get("tools", []):
            try:
                t = LatheTool.from_dict(td)
                tools_dict[t.tool_id] = t
            except Exception:
                pass

        proj = cls(
            name=str(data.get("name", path.stem)),
            stock=stock,
            contour=contour,
            tools=tools_dict if tools_dict else cls.default_tool_turret(),
            operations=ops,
            is_diameter_mode=bool(data.get("is_diameter_mode", True)),
            post_dialect=str(data.get("post_dialect", "linuxcnc")),
        )
        proj.recalculate_all()
        return proj
