from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MotionCmd:
    """Standardized internal lathe motion command.
    
    All coordinates are strictly in Radius Mode:
    - x: Radius in mm (scaled by 2.0 by post-processor in G7 Diameter Mode)
    - z: Axial coordinate in mm (Z=0 at front face, Z<0 toward chuck)
    - i: Incremental X center offset from arc start in mm (always radius, unscaled in G7)
    - k: Incremental Z center offset from arc start in mm
    - f: Feed rate in mm/rev (G95) or mm/min (G94)
    """
    mode: str  # 'G0', 'G1', 'G2', 'G3', 'G76', 'G83', 'G73', 'G40', 'G41', 'G42', 'SPINDLE_CSS', 'SPINDLE_RPM', 'TOOL_CHANGE', 'COMMENT'
    x: float | None = None
    z: float | None = None
    i: float | None = None
    k: float | None = None
    f: float | None = None
    raw_params: dict[str, Any] | None = None

    @classmethod
    def comment(cls, text: str) -> MotionCmd:
        return cls(mode="COMMENT", raw_params={"comment": text})

    @classmethod
    def rapid(cls, x: float | None = None, z: float | None = None) -> MotionCmd:
        return cls(mode="G0", x=x, z=z)

    @classmethod
    def linear(cls, x: float | None = None, z: float | None = None, f: float | None = None) -> MotionCmd:
        return cls(mode="G1", x=x, z=z, f=f)

    @classmethod
    def arc(cls, mode: str, x: float, z: float, i: float, k: float, f: float | None = None) -> MotionCmd:
        if mode not in ("G2", "G3"):
            raise ValueError(f"Arc mode must be 'G2' or 'G3', got '{mode}'")
        return cls(mode=mode, x=x, z=z, i=i, k=k, f=f)
