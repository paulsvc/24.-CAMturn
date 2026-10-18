from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence
import numpy as np

try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    OCP_AVAILABLE = True
except ImportError:
    OCP_AVAILABLE = False
    TopoDS_Shape = object  # type: ignore

from lathecam.cad.contour import Contour, chain_segments, extract_upper_silhouette
from lathecam.cad.geometry import Point2D


class STEPImporter:
    """Imports 3D B-Rep STEP/STP models using OpenCASCADE (OCP) and slices meridian 2D turning cross-sections."""

    def __init__(self, deflection_tolerance_mm: float = 0.005) -> None:
        if not OCP_AVAILABLE:
            raise RuntimeError(
                "OpenCASCADE (cadquery-ocp) is required to import STEP models but is not installed."
            )
        self.deflection_tolerance_mm = deflection_tolerance_mm

    def load_shape(self, filepath: str | Path) -> TopoDS_Shape:
        """Reads a .step or .stp file and returns the TopoDS_Shape."""
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"STEP file not found: {path}")

        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        if status != IFSelect_RetDone:
            raise ValueError(f"Failed to read STEP file {path} (Error status: {status})")

        reader.TransferRoots()
        shape = reader.OneShape()
        if shape.IsNull():
            raise ValueError(f"Loaded STEP shape from {path} is empty / null")

        return shape

    def _determine_spindle_axis(self, shape: TopoDS_Shape) -> str:
        """Determines the primary lathe spindle axis ('z', 'x', or 'y') by analyzing the 3D bounding box."""
        bbox = Bnd_Box()
        BRepBndLib.Add_s(shape, bbox)

        dx = bbox.GetXMax() - bbox.GetXMin()
        dy = bbox.GetYMax() - bbox.GetYMin()
        dz = bbox.GetZMax() - bbox.GetZMin()

        # In a turned part, the two radial axes will be roughly equal in span (circular cross section).
        diff_xy = abs(dx - dy)
        diff_yz = abs(dy - dz)
        diff_xz = abs(dx - dz)

        if diff_xy <= diff_yz and diff_xy <= diff_xz:
            return "z"
        elif diff_yz <= diff_xy and diff_yz <= diff_xz:
            return "x"
        else:
            return "y"

    def extract_contour(
        self,
        shape_or_path: TopoDS_Shape | str | Path,
        spindle_axis: str = "auto",
    ) -> Contour:
        """Slices the 3D solid with the meridian plane through the spindle axis and returns a 2D Contour.
        
        Args:
            shape_or_path: Either a file path (.step/.stp) or an existing TopoDS_Shape.
            spindle_axis: 'auto' (detects circular symmetry), 'z', 'x', or 'y'.
        """
        if isinstance(shape_or_path, (str, Path)):
            shape = self.load_shape(shape_or_path)
        else:
            shape = shape_or_path

        if spindle_axis == "auto":
            axis = self._determine_spindle_axis(shape)
        else:
            axis = spindle_axis.lower()

        # Set up cutting plane and coordinate projection mapping to (Z_axial, X_radius)
        # We cut through the center of the part with a plane passing through the origin
        if axis == "z":
            # Spindle along Z, radial along X. Meridian cutting plane is Y=0.
            plane = gp_Pln(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 1.0, 0.0))
            map_pt = lambda p: (float(p.Z()), float(p.X()))
        elif axis == "x":
            # Spindle along X, radial along Z. Meridian cutting plane is Y=0.
            plane = gp_Pln(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 1.0, 0.0))
            map_pt = lambda p: (float(p.X()), float(p.Z()))
        elif axis == "y":
            # Spindle along Y, radial along X. Meridian cutting plane is Z=0.
            plane = gp_Pln(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0))
            map_pt = lambda p: (float(p.Y()), float(p.X()))
        else:
            raise ValueError(f"Invalid spindle_axis '{spindle_axis}'. Expected 'auto', 'z', 'x', or 'y'")

        # Compute section
        section = BRepAlgoAPI_Section(shape, plane, True)
        section.Build()
        section_shape = section.Shape()

        # Extract all edges and discretize into polyline segments
        raw_segments: list[list[Point2D]] = []
        explorer = TopExp_Explorer(section_shape, TopAbs_EDGE)

        while explorer.More():
            edge = TopoDS.Edge(explorer.Current())
            curve_adaptor = BRepAdaptor_Curve(edge)

            # Adaptive deflection discretization
            try:
                discretizer = GCPnts_QuasiUniformDeflection(curve_adaptor, self.deflection_tolerance_mm)
                if discretizer.IsDone() and discretizer.NbPoints() >= 2:
                    seg_pts: list[Point2D] = []
                    for i in range(1, discretizer.NbPoints() + 1):
                        pnt = discretizer.Value(i)
                        seg_pts.append(map_pt(pnt))
                    if len(seg_pts) >= 2:
                        raw_segments.append(seg_pts)
                else:
                    # Fallback to evaluating curve bounds
                    u_first = curve_adaptor.FirstParameter()
                    u_last = curve_adaptor.LastParameter()
                    p1 = map_pt(curve_adaptor.Value(u_first))
                    p2 = map_pt(curve_adaptor.Value(u_last))
                    raw_segments.append([p1, p2])
            except Exception:
                # Fallback for degenerate edges
                try:
                    u_first = curve_adaptor.FirstParameter()
                    u_last = curve_adaptor.LastParameter()
                    p1 = map_pt(curve_adaptor.Value(u_first))
                    p2 = map_pt(curve_adaptor.Value(u_last))
                    raw_segments.append([p1, p2])
                except Exception:
                    pass

            explorer.Next()

        if not raw_segments:
            raise ValueError("No intersection curves found on the meridian section plane")

        # Connect segments topologically
        chains = chain_segments(raw_segments, tolerance_mm=0.05)
        if not chains:
            raise ValueError("Failed to chain section edges into continuous wire contours")

        # Extract upper silhouette, re-zero front face (max Z = 0.0), and orient front-to-rear
        contour = extract_upper_silhouette(chains, sample_step_mm=0.25)
        return contour
