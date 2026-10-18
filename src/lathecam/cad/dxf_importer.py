from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence
import ezdxf
import ezdxf.math

from lathecam.cad.contour import Contour, chain_segments, extract_upper_silhouette
from lathecam.cad.geometry import Point2D


def discretize_bulge(
    p1: tuple[float, float],
    p2: tuple[float, float],
    bulge: float,
    chordal_tolerance_mm: float = 0.005,
) -> list[Point2D]:
    """Converts a DXF polyline segment with a bulge into a discrete list of (Z, X) points.
    
    In DXF: bulge = tan(theta / 4) where theta is the included angle.
    """
    if abs(bulge) < 1e-6:
        return [p1, p2]

    try:
        center, start_angle, end_angle, radius = ezdxf.math.bulge_to_arc(
            ezdxf.math.Vec2(p1[0], p1[1]),
            ezdxf.math.Vec2(p2[0], p2[1]),
            bulge,
        )
    except Exception:
        return [p1, p2]

    # Calculate angular sweep
    if bulge > 0:
        if end_angle <= start_angle:
            end_angle += 2.0 * math.pi
    else:
        if end_angle >= start_angle:
            end_angle -= 2.0 * math.pi

    sweep = abs(end_angle - start_angle)
    # Chordal error: delta = R * (1 - cos(step / 2)) -> max_step = 2 * acos(1 - delta / R)
    cos_val = max(-1.0, 1.0 - chordal_tolerance_mm / radius)
    max_step = 2.0 * math.acos(cos_val) if cos_val < 1.0 else 0.1
    steps = max(4, int(math.ceil(sweep / max_step)))

    pts: list[Point2D] = []
    for step in range(steps + 1):
        t = step / steps
        angle = start_angle + t * (end_angle - start_angle)
        z = center.x + radius * math.cos(angle)
        x = center.y + radius * math.sin(angle)
        pts.append((float(z), float(x)))

    return pts


class DXFImporter:
    """Imports 2D DXF CAD files and extracts continuous upper-half turning contours."""

    def __init__(self, chordal_tolerance_mm: float = 0.005) -> None:
        self.chordal_tolerance_mm = chordal_tolerance_mm

    def load_contour(
        self,
        filepath: str | Path,
        axis_mapping: str = "auto",
        layers: Sequence[str] | None = None,
    ) -> Contour:
        """Loads a DXF file and extracts a clean, watertight turning Contour.
        
        Args:
            filepath: Path to the .dxf file.
            axis_mapping: 'auto' (longest axis is Z), 'x_to_z' (DXF X is Z, Y is radius),
                          or 'y_to_z' (DXF Y is Z, X is radius).
            layers: Optional list of DXF layer names to filter. If None, reads all visible model layers.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"DXF file not found: {path}")

        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()

        raw_segments: list[list[tuple[float, float]]] = []

        # 1. Process LWPOLYLINE entities
        for entity in msp.query("LWPOLYLINE"):
            if layers and entity.dxf.layer not in layers:
                continue
            pts_with_bulge = entity.get_points(format="xyb")
            if len(pts_with_bulge) < 2:
                continue

            poly_seg: list[tuple[float, float]] = []
            is_closed = entity.closed
            num_pts = len(pts_with_bulge)
            end_idx = num_pts if is_closed else num_pts - 1

            for i in range(end_idx):
                x1, y1, b = pts_with_bulge[i]
                x2, y2, _ = pts_with_bulge[(i + 1) % num_pts]

                if abs(b) > 1e-6:
                    arc_pts = discretize_bulge(
                        (x1, y1), (x2, y2), b, chordal_tolerance_mm=self.chordal_tolerance_mm
                    )
                    if poly_seg:
                        poly_seg.extend(arc_pts[1:])
                    else:
                        poly_seg.extend(arc_pts)
                else:
                    if not poly_seg:
                        poly_seg.append((x1, y1))
                    poly_seg.append((x2, y2))

            if poly_seg:
                raw_segments.append(poly_seg)

        # 2. Process standard LINE entities
        for entity in msp.query("LINE"):
            if layers and entity.dxf.layer not in layers:
                continue
            p_start = (float(entity.dxf.start.x), float(entity.dxf.start.y))
            p_end = (float(entity.dxf.end.x), float(entity.dxf.end.y))
            raw_segments.append([p_start, p_end])

        # 3. Process ARC entities
        for entity in msp.query("ARC"):
            if layers and entity.dxf.layer not in layers:
                continue
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_deg = entity.dxf.start_angle
            end_deg = entity.dxf.end_angle

            start_rad = math.radians(start_deg)
            end_rad = math.radians(end_deg)
            if end_rad <= start_rad:
                end_rad += 2.0 * math.pi

            sweep = end_rad - start_rad
            steps = max(6, int(math.ceil(sweep / 0.1)))
            arc_pts: list[tuple[float, float]] = []
            for s in range(steps + 1):
                ang = start_rad + (s / steps) * sweep
                arc_pts.append((center.x + radius * math.cos(ang), center.y + radius * math.sin(ang)))
            raw_segments.append(arc_pts)

        # 4. Process SPLINE entities
        for entity in msp.query("SPLINE"):
            if layers and entity.dxf.layer not in layers:
                continue
            try:
                spline_pts = [(float(p.x), float(p.y)) for p in entity.flattening(sagitta=self.chordal_tolerance_mm)]
                if len(spline_pts) >= 2:
                    raw_segments.append(spline_pts)
            except Exception:
                pass

        if not raw_segments:
            raise ValueError(f"No usable 2D geometry (LWPOLYLINE, LINE, ARC, SPLINE) found in {path}")

        # Determine axis mapping
        # In DXF: (x, y). We want (Z, X_radius).
        if axis_mapping == "auto":
            all_x = [pt[0] for seg in raw_segments for pt in seg]
            all_y = [pt[1] for seg in raw_segments for pt in seg]
            span_x = max(all_x) - min(all_x) if all_x else 0.0
            span_y = max(all_y) - min(all_y) if all_y else 0.0
            # Spindle axis (Z) is typically the longer dimension of a turned part
            map_x_to_z = span_x >= span_y
        elif axis_mapping == "x_to_z":
            map_x_to_z = True
        elif axis_mapping == "y_to_z":
            map_x_to_z = False
        else:
            raise ValueError(f"Unknown axis_mapping '{axis_mapping}'. Expected 'auto', 'x_to_z', or 'y_to_z'")

        # Map to (Z, X_radius)
        mapped_segments: list[list[Point2D]] = []
        for seg in raw_segments:
            if map_x_to_z:
                # DXF X -> Z, DXF Y -> X
                mapped_segments.append([(float(pt[0]), float(pt[1])) for pt in seg])
            else:
                # DXF Y -> Z, DXF X -> X
                mapped_segments.append([(float(pt[1]), float(pt[0])) for pt in seg])

        # Chain segments together
        chains = chain_segments(mapped_segments, tolerance_mm=0.05)
        if not chains:
            raise ValueError("Failed to connect DXF segments into continuous wire chains")

        # Extract upper silhouette, re-zero front face to Z=0.0, and order front-to-rear
        contour = extract_upper_silhouette(chains, sample_step_mm=0.25)
        return contour
