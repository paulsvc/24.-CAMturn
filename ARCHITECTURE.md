# LatheCAM - System Architecture & Engineering Specification

## 1. Executive Overview

**LatheCAM** is a desktop CAD/CAM application for CNC turning, engineered with a modern, dockable interface inspired by SolidWorks and Fusion 360. It enables machinists and engineers to import 3D CAD models (STEP) and 2D profiles (DXF), visualize and verify geometry in an interactive 3D/2D viewport, generate collision-free turning toolpaths using a custom **`Shapely` + `PyClipper` 2D geometric kernel**, and export production-ready G-code tailored for **LinuxCNC** lathes.

---

## 2. Core Technology Stack

| Layer | Technology | Justification |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.10 – 3.13+ | Orchestrates native C/C++ geometric backends with broad cross-platform compatibility. |
| **Desktop UI / Docking** | **PySide6 (Qt6)** | Industry-standard CAD GUI toolkit; supports native tabbed and floating `QDockWidget` layouts and hierarchical `QTreeView` models. |
| **Theme & UI Polish** | `pyqtdarktheme` | Provides a dark slate aesthetic matching modern engineering workbenches. |
| **B-Rep & STEP Engine** | **OpenCASCADE (`pythonocc-core` / `OCP`)** | Native C++ boundary-representation kernel required to parse STEP files and compute meridian cross-sections ($X-Z$ plane). |
| **2D CAD Ingestion** | **`ezdxf`** | Fast C-accelerated parsing of AutoCAD DXF files (splines, arcs, bulges, polylines). |
| **Lathe CAM Kernel** | **`shapely` (GEOS) & `pyclipper`** | Industrial C/C++ 2D boolean, polygon clipping, and parallel offsetting engines used for undercut shadowing, roughing passes, tool nose compensation, and 2D material removal verification. |
| **Arc Fitting** | **`numpy` / `scipy`** | Least-squares circular arc fitting (`G2`/`G3`) on discretized offset polylines within user-defined chordal tolerance. |
| **3D Rendering Viewport** | **PyVista (VTK)** or **OpenCASCADE AIS** | Hardware-accelerated OpenGL rendering of 3D solids, revolved stock cylinders, and interactive toolpath wireframes. |
| **G-Code Post Engine** | Custom Python Post-Processor | Formats coordinate axes, `G18` plane geometry, Constant Surface Speed (`G96 D- S-`), and LinuxCNC canned cycles (`G76`, `G83`). |

---

## 3. High-Level Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PySide6 (Qt6) Application                       │
│ ┌──────────────────┬─────────────────────────────────┬───────────────┐ │
│ │  Operations Dock │      3D Viewport (Canvas)       │ Property Dock │ │
│ │  - Feature Tree  │  - PyVista / OpenCASCADE AIS    │ - Operation   │ │
│ │  - Tool Library  │  - 3D Revolved Stock Simulation │   Parameters  │ │
│ │  - Stock Setup   │  - 2D Cross-Section Overlay     │ - Feed & Speed│ │
│ │                  │  - Toolpath Wireframe Overlay   │ - Tool Select │ │
│ └──────────────────┴─────────────────────────────────┴───────────────┘ │
└───────────────────┬─────────────────────────────────┬──────────────────┘
                    │                                 │
                    ▼                                 ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│          CAD Ingestion Engine         │ │        Tool Library          │
│ - STEP: pythonocc BRep Section (X-Z)  │ │ - Tool geometry (ISO/ANSI)   │
│ - DXF:  ezdxf Polyline Extraction     │ │ - Nose radius, tip angle     │
│ - Profile Normalizer (Radius Mode)    │ │ - Toolpost orientation (1-9) │
└───────────────────┬───────────────────┘ └──────────────┬───────────────┘
                    │                                    │
                    └─────────────────┬──────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Custom Shapely / PyClipper Turning Kernel                │
│  1. Undercut Shadowing: Clips profile against tool lead/clearance cone │
│  2. Boolean Stock Model: (Stock Box - Shadowed Part + Finish Allowance)│
│  3. Roughing Engine: Ray-cast / line intersection + 45° retract moves  │
│  4. Finishing Engine: PyClipper parallel offset (TNRC) + G2/G3 fitter  │
│  5. Parametric Ops: Threading (G76/G33), Peck Parting, Drilling (G83)  │
│  6. 2D Stock Simulator: Swept-tool boolean subtraction for gouge check │
└─────────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Post-Processor & G-Code Engine                     │
│  - Lathe Plane: G18 (Z-X) formatting                                   │
│  - Modes: G7 Diameter vs. G8 Radius coordinate scaling                 │
│  - Spindle: CSS (G96 D- S-) + Constant RPM (G97)                       │
│  - Dialects: LinuxCNC (.ngc), Fanuc, or expanded linear/arc moves      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Pipeline & Data Flow

```text
[ STEP / DXF File ]
         │
         ▼
[ CAD Importer ] ────> Extracts 2D polyline profile on the X-Z plane (X >= 0)
         │
         ▼
[ Shapely Shadow ] ──> Bridges undercuts exceeding tool lead & clearance angles
         │
         ▼
[ Stock Boolean ] ───> Computes Machinable Region = Stock_Box.difference(Part_Polygon)
         │
         ▼
[ Operation Solvers ]
   ├── Op 1: Face (Vertical X plunges from Stock OD to X=0 with Z step-overs)
   ├── Op 2: OD/ID Roughing (Horizontal Z-ray intersections with Machinable Region)
   ├── Op 3: Profile Finishing (PyClipper nose-radius offset + arc reconstruction)
   ├── Op 4: Threading (LinuxCNC G76 cycle + unrolled G33 preview passes)
   ├── Op 5: Grooving & Peck Part-off (Radial X pecking with chip-break retracts)
   └── Op 6: Axial Drilling (X0.0 center-line G83/G73 peck cycles)
         │
         ├──> [ 2D/3D Simulator ]: Subtracts swept tool polygon from Stock_Box
         │
         └──> [ Post-Processor ]: Emits final formatted LinuxCNC .ngc file
```

---

## 5. Repository Directory Layout

```text
lathe-cam/
├── ARCHITECTURE.md              # System design and specifications (this file)
├── ANTIGRAVITY_INSTRUCTIONS.md  # Agent rules, guardrails, and milestones
├── pyproject.toml               # Project config and binary wheel dependencies
├── requirements.txt             # Direct dependencies list
├── README.md                    # Setup, build, and run instructions
├── src/
│   └── lathecam/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       │
│       ├── cad/                 # CAD Ingestion & Slicing
│       │   ├── __init__.py
│       │   ├── step_importer.py # OpenCASCADE STEP loader and X-Z plane sectioner
│       │   ├── dxf_importer.py  # ezdxf profile parser
│       │   └── geometry.py      # Polyline, arc-fitting (G2/G3), and 2D vector math
│       │
│       ├── cam/                 # Pure Shapely / PyClipper Turning Kernel
│       │   ├── __init__.py
│       │   ├── commands.py      # Standardized MotionCmd (G0, G1, G2, G3) dataclasses
│       │   ├── tools.py         # Lathe tool definitions (CNMG, WNMG, DNMG, parting)
│       │   ├── shadowing.py     # Shapely tool clearance & undercut protection
│       │   ├── roughing.py      # Boolean stock subtraction & ray-intersection roughing
│       │   ├── finishing.py     # PyClipper nose-radius offset & G41/G42 compensation
│       │   ├── operations.py    # Facing, Threading (G76), Peck Parting, Drilling (G83)
│       │   └── simulator.py     # 2D Shapely swept-tool boolean material removal
│       │
│       ├── post/                # G-Code Post-Processors
│       │   ├── __init__.py
│       │   ├── base_post.py     # Abstract base post-processor
│       │   ├── linuxcnc.py      # LinuxCNC turning dialect (G18, G7/G8, G96 D, G76)
│       │   └── fanuc.py         # Fanuc 0i-TF turning dialect
│       │
│       ├── ui/                  # PySide6 Desktop Interface
│       │   ├── __init__.py
│       │   ├── main_window.py   # SolidWorks-style main frame and layout
│       │   ├── theme.py         # Dark mode styles and CAD palette
│       │   ├── docks/
│       │   │   ├── tree_dock.py      # FeatureManager operations tree
│       │   │   ├── properties_dock.py# Dynamic parameters inspector
│       │   │   └── tools_dock.py     # Tool library and turret selector
│       │   └── viewport/
│       │       ├── base_canvas.py    # Viewport abstract interface
│       │       └── vtk_viewport.py   # PyVista / VTK 3D lathe & toolpath canvas
│       │
│       └── models/              # Application Data Models
│           ├── project.py       # Serialized LatheCAM project state (.lcam)
│           └── stock.py         # Stock cylinder dimensions and work offsets
│
└── tests/
    ├── test_step_slicing.py     # Validation of STEP cross-section extraction
    ├── test_dxf_import.py       # Validation of DXF arc/polyline parsing
    ├── test_shadowing.py        # Validation of Shapely undercut clearance clipping
    ├── test_rough_finish.py     # Validation of Shapely roughing & PyClipper offsets
    └── test_post_processor.py   # LinuxCNC G-code syntax and arc offset tests
```

---

## 6. Key Subsystem Implementation Contracts

### 6.1 Standardized Motion Command (`cam/commands.py`)
All CAM operations output a unified list of internal commands stored strictly in **Radius Mode** (`x` = radius in mm):
```python
from dataclasses import dataclass

@dataclass
class MotionCmd:
    mode: str                 # 'G0', 'G1', 'G2', 'G3', 'G76', 'G83', 'COMMENT'
    x: float | None = None    # Radius in mm (scaled by 2.0 in post-processor if G7)
    z: float | None = None    # Axial Z coordinate in mm
    i: float | None = None    # Incremental X center offset (always radius)
    k: float | None = None    # Incremental Z center offset
    f: float | None = None    # Feed rate (mm/rev in G95)
    raw_params: dict | None = None # Used for canned cycles like G76 or G83
```

### 6.2 Tool Geometry Definition Contract (`cam/tools.py`)
```python
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
    tool_id: int
    name: str
    insert_shape: str          # e.g., 'C' (80 deg), 'D' (55 deg), 'V' (35 deg), 'W'
    nose_radius_mm: float      # e.g., 0.4, 0.8
    clearance_angle_deg: float # Trailing flank clearance angle
    lead_angle_deg: float      # Approach / lead angle (e.g., 95.0)
    orientation: ToolOrientation
    max_doc_mm: float          # Max depth of cut
```

### 6.3 Post-Processor Output Standards (`post/linuxcnc.py`)
- **Plane:** Mandatory `G18` (ZX-plane selection).
- **Coordinate Mode:** Default to `G7` (**Diameter Mode** where `X` = diameter, while arc center offsets `I` and `K` remain radius values).
- **Feed Mode:** Default to `G95` (feed per revolution: mm/rev).
- **Speed Mode:** Default to `G96 D{max_rpm} S{css_m_min}` (Constant Surface Speed) for turning and `G97 S{rpm}` for drilling and threading.