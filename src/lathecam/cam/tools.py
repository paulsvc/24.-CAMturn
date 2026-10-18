from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolOrientation(Enum):
    QUADRANT_1 = 1
    QUADRANT_2 = 2
    QUADRANT_3 = 3  # Standard OD right-hand turning (toward chuck)
    QUADRANT_4 = 4
    QUADRANT_5 = 5
    QUADRANT_6 = 6
    QUADRANT_7 = 7
    QUADRANT_8 = 8
    QUADRANT_9 = 9  # Centerline / neutral


@dataclass
class LatheTool:
    """Defines lathe tool geometry for turning operations, undercut shadowing, and TNRC."""
    tool_id: int
    name: str
    insert_shape: str          # e.g., 'C' (80 deg), 'D' (55 deg), 'V' (35 deg), 'W' (80 deg)
    nose_radius_mm: float      # e.g., 0.4, 0.8
    clearance_angle_deg: float # Trailing flank clearance angle (e.g. 5.0 deg)
    lead_angle_deg: float      # Approach / lead angle (e.g., 95.0 deg)
    orientation: ToolOrientation = ToolOrientation.QUADRANT_3
    max_doc_mm: float = 2.0    # Max depth of cut in mm
    tip_width_mm: float = 3.0  # Used for grooving / parting blades

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
        match self.orientation:
            case ToolOrientation.QUADRANT_1:
                return (+r, +r)
            case ToolOrientation.QUADRANT_2:
                return (-r, +r)
            case ToolOrientation.QUADRANT_3:
                return (-r, -r)
            case ToolOrientation.QUADRANT_4:
                return (+r, -r)
            case ToolOrientation.QUADRANT_5:
                return (+r, 0.0)
            case ToolOrientation.QUADRANT_6:
                return (0.0, +r)
            case ToolOrientation.QUADRANT_7:
                return (-r, 0.0)
            case ToolOrientation.QUADRANT_8:
                return (0.0, -r)
            case ToolOrientation.QUADRANT_9:
                return (0.0, 0.0)

    @classmethod
    def cnmg_roughing(cls, tool_id: int = 1, nose_radius_mm: float = 0.8) -> LatheTool:
        """Standard 80-degree diamond OD turning tool (PCLNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"CNMG {nose_radius_mm:.1f} OD Roughing",
            insert_shape="C",
            nose_radius_mm=nose_radius_mm,
            clearance_angle_deg=5.0,
            lead_angle_deg=95.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=2.5,
        )

    @classmethod
    def dnmg_finishing(cls, tool_id: int = 2, nose_radius_mm: float = 0.4) -> LatheTool:
        """Standard 55-degree diamond OD finishing tool (PDJNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"DNMG {nose_radius_mm:.1f} OD Finishing",
            insert_shape="D",
            nose_radius_mm=nose_radius_mm,
            clearance_angle_deg=25.0,
            lead_angle_deg=93.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=1.0,
        )

    @classmethod
    def vnmg_profiling(cls, tool_id: int = 3, nose_radius_mm: float = 0.4) -> LatheTool:
        """35-degree diamond profiling tool with high clearance (MVJNR/L)."""
        return cls(
            tool_id=tool_id,
            name=f"VNMG {nose_radius_mm:.1f} Profiling",
            insert_shape="V",
            nose_radius_mm=nose_radius_mm,
            clearance_angle_deg=45.0,
            lead_angle_deg=93.0,
            orientation=ToolOrientation.QUADRANT_3,
            max_doc_mm=1.0,
        )

    @classmethod
    def parting_blade(cls, tool_id: int = 4, width_mm: float = 3.0) -> LatheTool:
        """Parting and grooving blade."""
        return cls(
            tool_id=tool_id,
            name=f"Parting Blade {width_mm:.1f}mm",
            insert_shape="PART",
            nose_radius_mm=0.2,
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
            name="60deg OD Threading",
            insert_shape="THREAD",
            nose_radius_mm=0.1,
            clearance_angle_deg=25.0,
            lead_angle_deg=60.0,
            orientation=ToolOrientation.QUADRANT_8,
            max_doc_mm=1.5,
        )

    @classmethod
    def center_drill(cls, tool_id: int = 6, diameter_mm: float = 5.0) -> LatheTool:
        """Axial center drill / twist drill."""
        return cls(
            tool_id=tool_id,
            name=f"Drill {diameter_mm:.1f}mm",
            insert_shape="DRILL",
            nose_radius_mm=0.0,
            clearance_angle_deg=0.0,
            lead_angle_deg=118.0,
            orientation=ToolOrientation.QUADRANT_7,
            max_doc_mm=50.0,
            tip_width_mm=diameter_mm,
        )
