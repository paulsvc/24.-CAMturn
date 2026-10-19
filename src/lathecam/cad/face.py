from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Sequence

from lathecam.cad.contour import Contour
from lathecam.cad.geometry import (
    ArcSegment,
    LineSegment,
    Point2D,
    fit_arcs_to_polyline,
    point_line_distance,
)
from lathecam.cam.simulator import discretize_arc


class FaceType(Enum):
    CYLINDER = "Cylinder"
    SHOULDER = "Shoulder"
    TAPER = "Taper / Chamfer"
    FILLET = "Fillet / Radius"
    GROOVE = "Groove / Relief"


@dataclass
class TurnedFace:
    """Represents a discrete machinable topological face on a turned part contour."""

    face_id: str
    index: int
    face_type: FaceType
    start_pt: Point2D
    end_pt: Point2D
    points: list[Point2D] = field(default_factory=list)
    arc_radius_mm: float | None = None

    @property
    def z_max(self) -> float:
        return max(p[0] for p in self.points) if self.points else max(self.start_pt[0], self.end_pt[0])

    @property
    def z_min(self) -> float:
        return min(p[0] for p in self.points) if self.points else min(self.start_pt[0], self.end_pt[0])

    @property
    def x_max(self) -> float:
        return max(p[1] for p in self.points) if self.points else max(self.start_pt[1], self.end_pt[1])

    @property
    def x_min(self) -> float:
        return min(p[1] for p in self.points) if self.points else min(self.start_pt[1], self.end_pt[1])

    @property
    def dia_start_mm(self) -> float:
        return self.start_pt[1] * 2.0

    @property
    def dia_end_mm(self) -> float:
        return self.end_pt[1] * 2.0

    @property
    def dia_max_mm(self) -> float:
        return self.x_max * 2.0

    @property
    def axial_length_mm(self) -> float:
        return abs(self.z_max - self.z_min)

    @property
    def length_mm(self) -> float:
        pts = self.points if len(self.points) >= 2 else [self.start_pt, self.end_pt]
        return sum(
            math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            for p1, p2 in zip(pts[:-1], pts[1:])
        )

    @property
    def icon(self) -> str:
        return {
            FaceType.CYLINDER: "🟦",
            FaceType.SHOULDER: "🟧",
            FaceType.TAPER: "📐",
            FaceType.FILLET: "➰",
            FaceType.GROOVE: "🟪",
        }.get(self.face_type, "🔹")

    @property
    def name(self) -> str:
        return self.format_label(lang="en")

    def format_label(self, lang: str = "en") -> str:
        is_fr = lang == "fr"
        f_num = f"F{self.index}"
        if self.face_type == FaceType.CYLINDER:
            lbl = "Cylindre" if is_fr else "Cylinder"
            return f"{f_num}: {lbl} Ø{self.dia_max_mm:.1f} × {self.axial_length_mm:.1f}mm"
        if self.face_type == FaceType.GROOVE:
            lbl = "Gorge" if is_fr else "Groove"
            return f"{f_num}: {lbl} Ø{self.dia_max_mm:.1f} × {self.axial_length_mm:.1f}mm"
        if self.face_type == FaceType.SHOULDER:
            lbl = "Épaulement" if is_fr else "Shoulder"
            d1, d2 = min(self.dia_start_mm, self.dia_end_mm), max(self.dia_start_mm, self.dia_end_mm)
            return f"{f_num}: {lbl} Z={self.start_pt[0]:.1f} (Ø{d1:.1f}→{d2:.1f})"
        if self.face_type == FaceType.FILLET:
            lbl = "Congé" if is_fr else "Fillet"
            r_str = f"R{self.arc_radius_mm:.1f}mm" if self.arc_radius_mm else ""
            return f"{f_num}: {lbl} {r_str} (Z={self.z_max:.1f}..{self.z_min:.1f})"
        lbl = "Cône/Chanfrein" if is_fr else "Taper"
        return f"{f_num}: {lbl} Ø{self.dia_start_mm:.1f}→Ø{self.dia_end_mm:.1f} ({self.axial_length_mm:.1f}mm)"

    def distance_to_point(self, z: float, x: float) -> float:
        """Computes minimum Euclidean distance from (z, x_radius) to this face's polyline."""
        pts = self.points if len(self.points) >= 2 else [self.start_pt, self.end_pt]
        return min(
            point_line_distance((z, x), p1, p2)
            for p1, p2 in zip(pts[:-1], pts[1:])
        )


def decompose_contour_into_faces(contour: Contour) -> list[TurnedFace]:
    """Decomposes a continuous 2D turning contour into discrete machinable TurnedFace features."""
    pts = list(contour.points)
    if len(pts) < 2:
        return []
    if pts[0][0] < pts[-1][0]:
        pts.reverse()

    primitives = fit_arcs_to_polyline(pts, chordal_tolerance_mm=0.015, min_arc_points=4)
    faces: list[TurnedFace] = []

    for idx, prim in enumerate(primitives, start=1):
        face_id = f"face_{idx}"
        if isinstance(prim, ArcSegment):
            arc_pts = discretize_arc(prim.start, prim.end, prim.center, mode=prim.mode)
            faces.append(
                TurnedFace(
                    face_id=face_id,
                    index=idx,
                    face_type=FaceType.FILLET,
                    start_pt=prim.start,
                    end_pt=prim.end,
                    points=arc_pts,
                    arc_radius_mm=prim.radius,
                )
            )
        elif isinstance(prim, LineSegment):
            dz = abs(prim.end[0] - prim.start[0])
            dx = abs(prim.end[1] - prim.start[1])

            if dx < 0.05 and dz >= 0.05:
                # Check if recessed groove between two shoulders with higher radius
                prev_r = primitives[idx - 2].start[1] if idx >= 2 else prim.start[1]
                next_r = primitives[idx].end[1] if idx < len(primitives) else prim.end[1]
                cur_r = 0.5 * (prim.start[1] + prim.end[1])
                if prev_r > cur_r + 0.2 and next_r > cur_r + 0.2:
                    f_type = FaceType.GROOVE
                else:
                    f_type = FaceType.CYLINDER
            elif dz < 0.05 and dx >= 0.05:
                f_type = FaceType.SHOULDER
            else:
                f_type = FaceType.TAPER

            faces.append(
                TurnedFace(
                    face_id=face_id,
                    index=idx,
                    face_type=f_type,
                    start_pt=prim.start,
                    end_pt=prim.end,
                    points=[prim.start, prim.end],
                )
            )

    return faces
