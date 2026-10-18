from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence
import shapely.geometry
import shapely.ops

from lathecam.cad.geometry import Point2D
from lathecam.cam.commands import MotionCmd
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


@dataclass
class SimulationResult:
    remaining_stock: shapely.geometry.Polygon | shapely.geometry.MultiPolygon
    uncut_rest_material: shapely.geometry.Polygon | shapely.geometry.MultiPolygon
    gouge_polygon: shapely.geometry.Polygon | shapely.geometry.MultiPolygon
    gouge_area_mm2: float
    rest_area_mm2: float

    @property
    def is_gouged(self) -> bool:
        return self.gouge_area_mm2 > 1e-4


def discretize_arc(
    start: Point2D,
    end: Point2D,
    center: Point2D,
    mode: str,
    max_chord_error_mm: float = 0.01,
) -> list[Point2D]:
    """Discretizes a circular arc into a sequence of line points in (Z, X) space."""
    zc, xc = center
    z1, x1 = start
    z2, x2 = end

    r = math.hypot(z1 - zc, x1 - xc)
    if r < 1e-6:
        return [start, end]

    theta1 = math.atan2(x1 - xc, z1 - zc)
    theta2 = math.atan2(x2 - xc, z2 - zc)

    if mode == "G2":  # Clockwise
        if theta2 >= theta1:
            theta2 -= 2.0 * math.pi
    else:  # Counter-clockwise (G3)
        if theta2 <= theta1:
            theta2 += 2.0 * math.pi

    d_theta = abs(theta2 - theta1)
    # Chord error formula: delta = r * (1 - cos(d_step / 2)) -> d_step = 2 * acos(1 - delta/r)
    cos_val = max(-1.0, 1.0 - max_chord_error_mm / r)
    max_step = 2.0 * math.acos(cos_val) if cos_val < 1.0 else 0.1
    steps = max(4, int(math.ceil(d_theta / max_step)))

    pts: list[Point2D] = []
    for step in range(steps + 1):
        t = step / steps
        theta = theta1 + t * (theta2 - theta1)
        pts.append((zc + r * math.cos(theta), xc + r * math.sin(theta)))

    return pts


def simulate_2d_material_removal(
    stock: Stock,
    target_part_poly: shapely.geometry.Polygon | shapely.geometry.MultiPolygon,
    commands: Sequence[MotionCmd],
    tool: LatheTool,
) -> SimulationResult:
    """Simulates 2D material removal in (Z, X_radius) space.
    
    Subtracts the swept cutting tool footprint from stock_box and calculates:
    1. remaining_stock = stock_box - cut_geometries
    2. uncut_rest_material = remaining_stock - target_part_poly
    3. gouge_polygon = target_part_poly.intersection(cut_geometries)
    """
    stock_box = stock.to_shapely_box()
    cut_polys: list[shapely.geometry.Polygon] = []

    current_pos: Point2D | None = None
    r_nose = min(0.15, max(0.05, tool.nose_radius_mm * 0.2))

    for cmd in commands:
        if cmd.mode == "COMMENT":
            continue

        if cmd.mode == "G0":
            if cmd.z is not None and cmd.x is not None:
                current_pos = (cmd.z, cmd.x)
            elif cmd.z is not None and current_pos is not None:
                current_pos = (cmd.z, current_pos[1])
            elif cmd.x is not None and current_pos is not None:
                current_pos = (current_pos[0], cmd.x)
            continue

        if cmd.mode in ("G1", "G41", "G42"):
            if current_pos is None:
                if cmd.z is not None and cmd.x is not None:
                    current_pos = (cmd.z, cmd.x)
                continue

            target_z = cmd.z if cmd.z is not None else current_pos[0]
            target_x = cmd.x if cmd.x is not None else current_pos[1]
            end_pos: Point2D = (target_z, target_x)

            if math.hypot(end_pos[0] - current_pos[0], end_pos[1] - current_pos[1]) > 1e-6:
                ls = shapely.geometry.LineString([current_pos, end_pos])
                cut_poly = ls.buffer(r_nose, cap_style="round", join_style="round")
                if not cut_poly.is_empty:
                    cut_polys.append(cut_poly)

            current_pos = end_pos

        elif cmd.mode in ("G2", "G3"):
            if current_pos is None or cmd.z is None or cmd.x is None or cmd.i is None or cmd.k is None:
                continue

            # In G18: i is X offset, k is Z offset from start position
            center: Point2D = (current_pos[0] + cmd.k, current_pos[1] + cmd.i)
            end_pos = (cmd.z, cmd.x)

            arc_pts = discretize_arc(current_pos, end_pos, center, mode=cmd.mode)
            if len(arc_pts) >= 2:
                ls = shapely.geometry.LineString(arc_pts)
                cut_poly = ls.buffer(r_nose, cap_style="round", join_style="round")
                if not cut_poly.is_empty:
                    cut_polys.append(cut_poly)

            current_pos = end_pos

        elif cmd.mode in ("G83", "G73"):
            # Axial drilling from centerline
            target_z = cmd.z if cmd.z is not None else -10.0
            drill_radius = tool.tip_width_mm / 2.0 if tool.tip_width_mm > 0 else 2.5
            drill_poly = shapely.geometry.box(target_z, 0.0, stock.z_start_mm, drill_radius)
            cut_polys.append(drill_poly)
            current_pos = (target_z, 0.0)

    if not cut_polys:
        remaining = stock_box
        rest = remaining.difference(target_part_poly)
        return SimulationResult(
            remaining_stock=remaining,
            uncut_rest_material=rest,
            gouge_polygon=shapely.geometry.Polygon(),
            gouge_area_mm2=0.0,
            rest_area_mm2=rest.area,
        )

    # Union all swept cut footprints
    all_cuts = shapely.ops.unary_union(cut_polys)

    remaining_stock = stock_box.difference(all_cuts)
    uncut_rest = remaining_stock.difference(target_part_poly)
    gouge = target_part_poly.intersection(all_cuts)

    # Subtract tolerance boundary to avoid float roundoff false gouges
    cleaned_gouge = gouge.difference(target_part_poly.boundary.buffer(1e-4))

    return SimulationResult(
        remaining_stock=remaining_stock,
        uncut_rest_material=uncut_rest,
        gouge_polygon=cleaned_gouge,
        gouge_area_mm2=cleaned_gouge.area,
        rest_area_mm2=uncut_rest.area,
    )
