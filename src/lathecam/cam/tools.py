from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolOrientation(Enum):
    QUADRANT_1 = 1
    QUADRANT_2 = 2
    QUADRANT_3 = 3  # Standard OD right-hand turning (toward chuck)
    QUADRANT_4 = 4
    QUADRANT_5 = 5
    QUADRANT_6 = 6
    QUADRANT_7 = 7  # Axial drill / boring
    QUADRANT_8 = 8  # Facing / threading
    QUADRANT_9 = 9  # Centerline / round insert


ISO_SHAPE_DESCRIPTIONS: dict[str, str] = {
    "C": "80° Rhombic / Diamond (CNMG, CCMT)",
    "D": "55° Rhombic / Diamond (DNMG, DCMT)",
    "V": "35° Rhombic / Diamond (VNMG, VBMT)",
    "W": "80° Trigon (WNMG)",
    "T": "60° Triangular (TNMG, TCMT)",
    "S": "90° Square (SNMG, SCMT)",
    "R": "Round / Circular (RNMG, RCMT)",
    "K": "55° Parallelogram (KNUX)",
    "PART": "Parting & Grooving Blade",
    "THREAD": "60° External/Internal Threading",
    "DRILL": "Axial Twist / Center Drill",
}


@dataclass
class LatheTool:
    """Defines lathe tool and ISO insert geometry for turning operations, undercut shadowing, and TNRC."""
    tool_id: int
    name: str
    insert_shape: str = "C"             # "C", "D", "V", "W", "T", "S", "R", "K", "PART", "THREAD", "DRILL"
    inscribed_circle_mm: float = 12.7   # IC (d) in mm
    thickness_mm: float = 4.76          # s in mm
    nose_radius_mm: float = 0.8         # r_epsilon in mm
    cutting_edge_length_mm: float = 12.0# l in mm
    clearance_angle_deg: float = 5.0    # Trailing flank clearance angle (deg)
    lead_angle_deg: float = 95.0        # Approach / lead angle (deg)
    orientation: ToolOrientation = ToolOrientation.QUADRANT_3
    max_doc_mm: float = 2.0             # Max depth of cut in mm
    tip_width_mm: float = 3.0           # Used for grooving / parting blades & drill diameter
    hand: str = "R"                     # "R", "L", "N"

    def virtual_tip_offset(self) -> tuple[float, float]:
        """Returns (dz, dx) offset from the tool nose arc center to the virtual tool tip.
        
        Coordinates are in (Z, X_radius) mm:
        LinuxCNC Tool Orientation Table:
        1: (+r, +r)
        2: (-r, +r)
        3: (-r, -r) [Standard OD right-hand turning toward chuck]
        4: (+r, -r)
        5: (+r,  0)
        6: ( 0, +r)
        7: (-r,  0)
        8: ( 0, -r)
        9: ( 0,  0) [Nose arc center / round insert]
        """
        r = self.nose_radius_mm
        offsets = {
            ToolOrientation.QUADRANT_1: (+r, +r),
            ToolOrientation.QUADRANT_2: (-r, +r),
            ToolOrientation.QUADRANT_3: (-r, -r),
            ToolOrientation.QUADRANT_4: (+r, -r),
            ToolOrientation.QUADRANT_5: (+r, 0.0),
            ToolOrientation.QUADRANT_6: (0.0, +r),
            ToolOrientation.QUADRANT_7: (-r, 0.0),
            ToolOrientation.QUADRANT_8: (0.0, -r),
            ToolOrientation.QUADRANT_9: (0.0, 0.0),
        }
        return offsets.get(self.orientation, (0.0, 0.0))

    def to_dict(self) -> dict[str, Any]:
        """Serializes tool properties to a dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "insert_shape": self.insert_shape,
            "inscribed_circle_mm": self.inscribed_circle_mm,
            "thickness_mm": self.thickness_mm,
            "nose_radius_mm": self.nose_radius_mm,
            "cutting_edge_length_mm": self.cutting_edge_length_mm,
            "clearance_angle_deg": self.clearance_angle_deg,
            "lead_angle_deg": self.lead_angle_deg,
            "orientation": self.orientation.value,
            "max_doc_mm": self.max_doc_mm,
            "tip_width_mm": self.tip_width_mm,
            "hand": self.hand,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LatheTool:
        """Constructs a LatheTool instance from a dictionary."""
        orient_raw = data.get("orientation", 3)
        if isinstance(orient_raw, ToolOrientation):
            orient = orient_raw
        elif isinstance(orient_raw, str) and orient_raw.isdigit():
            orient = ToolOrientation(int(orient_raw))
        elif isinstance(orient_raw, int):
            orient = ToolOrientation(orient_raw)
        else:
            orient = ToolOrientation.QUADRANT_3

        return cls(
            tool_id=int(data["tool_id"]),
            name=str(data["name"]),
            insert_shape=str(data.get("insert_shape", "C")),
            inscribed_circle_mm=float(data.get("inscribed_circle_mm", 12.7)),
            thickness_mm=float(data.get("thickness_mm", 4.76)),
            nose_radius_mm=float(data.get("nose_radius_mm", 0.8)),
            cutting_edge_length_mm=float(data.get("cutting_edge_length_mm", 12.0)),
            clearance_angle_deg=float(data.get("clearance_angle_deg", 5.0)),
            lead_angle_deg=float(data.get("lead_angle_deg", 95.0)),
            orientation=orient,
            max_doc_mm=float(data.get("max_doc_mm", 2.0)),
            tip_width_mm=float(data.get("tip_width_mm", 3.0)),
            hand=str(data.get("hand", "R")),
        )

    def clone(self, new_tool_id: int | None = None) -> LatheTool:
        """Creates a copy of the tool, optionally with a new pocket ID."""
        d = self.to_dict()
        if new_tool_id is not None:
            d["tool_id"] = new_tool_id
            d["name"] = f"{self.name} (Copy)"
        return LatheTool.from_dict(d)

    def apply_preset(self, preset_key: str) -> bool:
        """Applies dimensional parameters from an ISO insert preset."""
        preset = ISO_INSERT_PRESETS.get(preset_key)
        if not preset:
            return False
        self.insert_shape = preset["insert_shape"]
        self.inscribed_circle_mm = preset["inscribed_circle_mm"]
        self.thickness_mm = preset["thickness_mm"]
        self.nose_radius_mm = preset["nose_radius_mm"]
        self.cutting_edge_length_mm = preset.get("cutting_edge_length_mm", 12.0)
        self.clearance_angle_deg = preset["clearance_angle_deg"]
        self.lead_angle_deg = preset["lead_angle_deg"]
        self.orientation = preset["orientation"]
        self.max_doc_mm = preset["max_doc_mm"]
        if "tip_width_mm" in preset:
            self.tip_width_mm = preset["tip_width_mm"]
        self.name = preset.get("name", self.name)
        return True

    @classmethod
    def cnmg_roughing(cls, tool_id: int = 1, nose_radius_mm: float = 0.8) -> LatheTool:
        """Standard 80-degree diamond OD turning tool (PCLNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"CNMG 120408 OD Roughing" if nose_radius_mm == 0.8 else f"CNMG {nose_radius_mm:.1f} OD Roughing",
            insert_shape="C",
            inscribed_circle_mm=12.7,
            thickness_mm=4.76,
            nose_radius_mm=nose_radius_mm,
            cutting_edge_length_mm=12.9,
            clearance_angle_deg=5.0,
            lead_angle_deg=95.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=2.5,
            tip_width_mm=3.0,
        )

    @classmethod
    def dnmg_finishing(cls, tool_id: int = 2, nose_radius_mm: float = 0.4) -> LatheTool:
        """Standard 55-degree diamond OD finishing tool (PDJNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"DNMG 150604 OD Finishing" if nose_radius_mm == 0.4 else f"DNMG {nose_radius_mm:.1f} OD Finishing",
            insert_shape="D",
            inscribed_circle_mm=12.7,
            thickness_mm=6.35,
            nose_radius_mm=nose_radius_mm,
            cutting_edge_length_mm=15.5,
            clearance_angle_deg=25.0,
            lead_angle_deg=93.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=1.2,
            tip_width_mm=3.0,
        )

    @classmethod
    def vnmg_profiling(cls, tool_id: int = 3, nose_radius_mm: float = 0.4) -> LatheTool:
        """35-degree diamond profiling tool with high clearance (MVJNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"VNMG 160404 Profiling" if nose_radius_mm == 0.4 else f"VNMG {nose_radius_mm:.1f} Profiling",
            insert_shape="V",
            inscribed_circle_mm=9.525,
            thickness_mm=4.76,
            nose_radius_mm=nose_radius_mm,
            cutting_edge_length_mm=16.6,
            clearance_angle_deg=45.0,
            lead_angle_deg=93.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=1.0,
            tip_width_mm=3.0,
        )

    @classmethod
    def parting_blade(cls, tool_id: int = 4, width_mm: float = 3.0) -> LatheTool:
        """Parting and grooving blade."""
        return cls(
            tool_id=tool_id,
            name=f"Parting Blade {width_mm:.1f}mm",
            insert_shape="PART",
            inscribed_circle_mm=12.0,
            thickness_mm=2.4,
            nose_radius_mm=0.2,
            cutting_edge_length_mm=20.0,
            clearance_angle_deg=1.0,
            lead_angle_deg=90.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=width_mm,
            tip_width_mm=width_mm,
        )

    @classmethod
    def threading_tool(cls, tool_id: int = 5) -> LatheTool:
        """Standard 60-degree OD threading tool."""
        return cls(
            tool_id=tool_id,
            name="60deg OD Threading 16ER",
            insert_shape="THREAD",
            inscribed_circle_mm=9.525,
            thickness_mm=3.66,
            nose_radius_mm=0.1,
            cutting_edge_length_mm=16.0,
            clearance_angle_deg=25.0,
            lead_angle_deg=60.0,
            orientation=ToolOrientation.QUADRANT_8,
            max_doc_mm=1.5,
            tip_width_mm=3.0,
        )

    @classmethod
    def center_drill(cls, tool_id: int = 6, diameter_mm: float = 5.0) -> LatheTool:
        """Axial center drill / twist drill."""
        return cls(
            tool_id=tool_id,
            name=f"Drill Ø{diameter_mm:.1f}mm",
            insert_shape="DRILL",
            inscribed_circle_mm=diameter_mm,
            thickness_mm=diameter_mm,
            nose_radius_mm=0.0,
            cutting_edge_length_mm=50.0,
            clearance_angle_deg=0.0,
            lead_angle_deg=118.0,
            orientation=ToolOrientation.QUADRANT_7,
            max_doc_mm=50.0,
            tip_width_mm=diameter_mm,
        )


ISO_INSERT_PRESETS: dict[str, dict[str, Any]] = {
    "CNMG 120408": {
        "insert_shape": "C",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 12.9,
        "clearance_angle_deg": 5.0,
        "lead_angle_deg": 95.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.5,
        "name": "CNMG 120408 OD Roughing",
    },
    "CNMG 120404": {
        "insert_shape": "C",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.4,
        "cutting_edge_length_mm": 12.9,
        "clearance_angle_deg": 5.0,
        "lead_angle_deg": 95.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.0,
        "name": "CNMG 120404 Semi-Finish",
    },
    "DNMG 150604": {
        "insert_shape": "D",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 6.35,
        "nose_radius_mm": 0.4,
        "cutting_edge_length_mm": 15.5,
        "clearance_angle_deg": 25.0,
        "lead_angle_deg": 93.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 1.2,
        "name": "DNMG 150604 OD Finishing",
    },
    "DNMG 150608": {
        "insert_shape": "D",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 6.35,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 15.5,
        "clearance_angle_deg": 25.0,
        "lead_angle_deg": 93.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 1.8,
        "name": "DNMG 150608 OD Finishing",
    },
    "VNMG 160404": {
        "insert_shape": "V",
        "inscribed_circle_mm": 9.525,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.4,
        "cutting_edge_length_mm": 16.6,
        "clearance_angle_deg": 45.0,
        "lead_angle_deg": 93.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 1.0,
        "name": "VNMG 160404 Profiling",
    },
    "VNMG 160408": {
        "insert_shape": "V",
        "inscribed_circle_mm": 9.525,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 16.6,
        "clearance_angle_deg": 45.0,
        "lead_angle_deg": 93.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 1.5,
        "name": "VNMG 160408 Profiling",
    },
    "WNMG 080408": {
        "insert_shape": "W",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 8.7,
        "clearance_angle_deg": 5.0,
        "lead_angle_deg": 95.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.5,
        "name": "WNMG 080408 Trigon Turning",
    },
    "TNMG 160408": {
        "insert_shape": "T",
        "inscribed_circle_mm": 9.525,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 16.5,
        "clearance_angle_deg": 7.0,
        "lead_angle_deg": 91.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.0,
        "name": "TNMG 160408 Triangular",
    },
    "SNMG 120408": {
        "insert_shape": "S",
        "inscribed_circle_mm": 12.7,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.8,
        "cutting_edge_length_mm": 12.7,
        "clearance_angle_deg": 15.0,
        "lead_angle_deg": 45.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 3.0,
        "name": "SNMG 120408 Square Chamfer",
    },
    "RCMT 1204MO": {
        "insert_shape": "R",
        "inscribed_circle_mm": 12.0,
        "thickness_mm": 4.76,
        "nose_radius_mm": 6.0,
        "cutting_edge_length_mm": 12.0,
        "clearance_angle_deg": 7.0,
        "lead_angle_deg": 90.0,
        "orientation": ToolOrientation.QUADRANT_9,
        "max_doc_mm": 2.5,
        "name": "RCMT 1204 Round Copy",
    },
    "KNUX 160405R": {
        "insert_shape": "K",
        "inscribed_circle_mm": 9.525,
        "thickness_mm": 4.76,
        "nose_radius_mm": 0.5,
        "cutting_edge_length_mm": 16.5,
        "clearance_angle_deg": 5.0,
        "lead_angle_deg": 93.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.0,
        "name": "KNUX 160405R Parallelogram",
    },
    "Parting Blade 3.0mm": {
        "insert_shape": "PART",
        "inscribed_circle_mm": 12.0,
        "thickness_mm": 2.4,
        "nose_radius_mm": 0.2,
        "tip_width_mm": 3.0,
        "cutting_edge_length_mm": 20.0,
        "clearance_angle_deg": 1.0,
        "lead_angle_deg": 90.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 3.0,
        "name": "Parting Blade 3.0mm",
    },
    "Parting Blade 2.0mm": {
        "insert_shape": "PART",
        "inscribed_circle_mm": 10.0,
        "thickness_mm": 1.8,
        "nose_radius_mm": 0.2,
        "tip_width_mm": 2.0,
        "cutting_edge_length_mm": 18.0,
        "clearance_angle_deg": 1.0,
        "lead_angle_deg": 90.0,
        "orientation": ToolOrientation.QUADRANT_3,
        "max_doc_mm": 2.0,
        "name": "Parting Blade 2.0mm",
    },
    "60° Threading 16ER": {
        "insert_shape": "THREAD",
        "inscribed_circle_mm": 9.525,
        "thickness_mm": 3.66,
        "nose_radius_mm": 0.1,
        "cutting_edge_length_mm": 16.0,
        "clearance_angle_deg": 25.0,
        "lead_angle_deg": 60.0,
        "orientation": ToolOrientation.QUADRANT_8,
        "max_doc_mm": 1.5,
        "name": "60deg OD Threading 16ER",
    },
    "Twist Drill Ø5.0mm": {
        "insert_shape": "DRILL",
        "inscribed_circle_mm": 5.0,
        "thickness_mm": 5.0,
        "nose_radius_mm": 0.0,
        "tip_width_mm": 5.0,
        "cutting_edge_length_mm": 50.0,
        "clearance_angle_deg": 0.0,
        "lead_angle_deg": 118.0,
        "orientation": ToolOrientation.QUADRANT_7,
        "max_doc_mm": 50.0,
        "name": "Drill Ø5.0mm",
    },
    "Twist Drill Ø10.0mm": {
        "insert_shape": "DRILL",
        "inscribed_circle_mm": 10.0,
        "thickness_mm": 10.0,
        "nose_radius_mm": 0.0,
        "tip_width_mm": 10.0,
        "cutting_edge_length_mm": 70.0,
        "clearance_angle_deg": 0.0,
        "lead_angle_deg": 118.0,
        "orientation": ToolOrientation.QUADRANT_7,
        "max_doc_mm": 70.0,
        "name": "Drill Ø10.0mm",
    },
}
