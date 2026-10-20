from __future__ import annotations

from typing import Sequence
import shapely.geometry
import shapely.ops

from lathecam.cad.geometry import Point2D
from lathecam.cam.commands import MotionCmd
from lathecam.cam.shadowing import compute_shadowed_polygon
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


def generate_roughing_toolpath(
    profile_pts: Sequence[Point2D],
    stock: Stock,
    tool: LatheTool,
    doc_mm: float | None = None,
    feed_mm_rev: float = 0.25,
    finish_allowance_mm: float = 0.5,
    retract_mm: float = 0.8,
    clearance_z_mm: float = 1.0,
    clearance_x_mm: float = 1.0,
    is_id: bool = False,
    z_start: float | None = None,
    z_end: float | None = None,
) -> list[MotionCmd]:
    """Generates an OD or ID roughing toolpath with horizontal slicing and 45-degree retracts.
    
    All coordinates and offsets are in Radius Mode (X = radius in mm).
    Optionally restricts cutting to [min(z_start, z_end), max(z_start, z_end)].
    """
    if doc_mm is None or doc_mm <= 0:
        doc_mm = tool.max_doc_mm

    # 1. Compute shadowed part polygon with clearance protection
    shadowed_poly = compute_shadowed_polygon(
        profile_pts,
        tool,
        z_min_bound=stock.z_end_mm,
        z_max_bound=stock.z_start_mm,
    )

    # For OD roughing, internal bores/holes below the outer turning silhouette are
    # machined by drilling/boring, not by external turning tools.
    if not is_id:
        from lathecam.cam.shadowing import extract_upper_profile, profile_to_polygon
        upper_pts = extract_upper_profile(shadowed_poly)
        if len(upper_pts) >= 2:
            shadowed_poly = profile_to_polygon(
                upper_pts,
                z_min=stock.z_end_mm,
                z_max=stock.z_start_mm,
            )

    # 2. Apply finish allowance
    if finish_allowance_mm > 0:
        buffered_part = shadowed_poly.buffer(finish_allowance_mm, join_style="round")
    else:
        buffered_part = shadowed_poly

    # 3. Compute machinable region: Stock_Box - Buffered_Part
    stock_box = stock.to_shapely_box()
    machinable_region = stock_box.difference(buffered_part)

    # 3b. Clip to axial Z bounds if specified (Face / Custom Range selection)
    if z_start is not None or z_end is not None:
        z1 = z_start if z_start is not None else stock.z_start_mm
        z2 = z_end if z_end is not None else stock.z_end_mm
        z_high = max(z1, z2)
        z_low = min(z1, z2)
        if z_high - z_low < 0.2:
            z_high += 0.5
            z_low -= 0.5
        clip_box = shapely.geometry.box(z_low, 0.0, z_high, stock.od_radius + 10.0)
        machinable_region = machinable_region.intersection(clip_box)

    if machinable_region.is_empty:
        return [MotionCmd.comment("Machinable region is empty; stock already at or within part profile")]

    commands: list[MotionCmd] = []
    commands.append(MotionCmd.comment(f"Begin {'ID' if is_id else 'OD'} Roughing Pass (DOC: {doc_mm:.2f}mm, Feed: {feed_mm_rev:.3f}mm/rev)"))

    # Safe clearance coordinates
    safe_x = stock.od_radius + clearance_x_mm if not is_id else max(0.0, stock.id_radius - clearance_x_mm)
    safe_z = stock.z_start_mm + clearance_z_mm

    # Rapid to initial safe start position
    commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))

    # Determine slicing range
    min_z, min_x, max_z, max_x = machinable_region.bounds

    if not is_id:
        # OD Roughing: Step down in X from stock.od_radius - doc_mm to min_x
        current_x = stock.od_radius - doc_mm
        target_min_x = min_x
        step_dir = -1.0
    else:
        # ID Roughing: Step up in X from stock.id_radius + doc_mm to max_x
        current_x = stock.id_radius + doc_mm
        target_min_x = max_x
        step_dir = +1.0

    while (step_dir < 0 and current_x >= target_min_x - 1e-4) or (step_dir > 0 and current_x <= target_min_x + 1e-4):
        # Ray across full Z range of stock
        ray = shapely.geometry.LineString([
            (stock.z_end_mm - 1.0, current_x),
            (stock.z_start_mm + 1.0, current_x),
        ])

        inter = ray.intersection(machinable_region)
        if not inter.is_empty:
            segments: list[shapely.geometry.LineString] = []
            if isinstance(inter, shapely.geometry.LineString):
                segments.append(inter)
            elif isinstance(inter, shapely.geometry.MultiLineString):
                segments.extend(inter.geoms)
            elif isinstance(inter, shapely.geometry.GeometryCollection):
                for g in inter.geoms:
                    if isinstance(g, shapely.geometry.LineString):
                        segments.append(g)

            # Filter out tiny noise segments
            valid_segments = [s for s in segments if s.length > 0.05]

            # In turning, cuts proceed from front (+Z) to back (-Z).
            # Extract and order segments from right (+Z) to left (-Z).
            ordered_cuts: list[tuple[float, float]] = []
            for s in valid_segments:
                coords = list(s.coords)
                z_vals = [c[0] for c in coords]
                z_high = max(z_vals)
                z_low = min(z_vals)
                ordered_cuts.append((z_high, z_low))

            # Sort descending by z_high (front to rear)
            ordered_cuts.sort(key=lambda c: c[0], reverse=True)

            for z_high, z_low in ordered_cuts:
                approach_z = z_high + clearance_z_mm
                approach_x = current_x - step_dir * min(clearance_x_mm, doc_mm)
                # 1. Rapid axially at safe X to approach_z, then radially to approach_x
                commands.append(MotionCmd.rapid(x=safe_x, z=approach_z))
                commands.append(MotionCmd.rapid(x=approach_x, z=approach_z))
                # 2. Feed radially to cutting depth
                commands.append(MotionCmd.linear(x=current_x, z=approach_z, f=feed_mm_rev))
                # 3. Feed cut along Z towards chuck
                commands.append(MotionCmd.linear(x=current_x, z=z_low, f=feed_mm_rev))
                # 4. 45-degree clearance retract move (+dZ away from cut direction, +dX away from workpiece)
                retract_x = current_x - step_dir * retract_mm
                retract_z = z_low + retract_mm
                commands.append(MotionCmd.linear(x=retract_x, z=retract_z, f=feed_mm_rev * 1.5))
                # 5. Radial rapid out to safe clearance diameter at retract_z
                commands.append(MotionCmd.rapid(x=safe_x, z=retract_z))

        current_x += step_dir * doc_mm

    commands.append(MotionCmd.rapid(x=safe_x, z=safe_z))
    commands.append(MotionCmd.comment("End Roughing Pass"))
    return commands

