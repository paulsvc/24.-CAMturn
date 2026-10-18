# LatheCAM - System Architecture & Engineering Specification

## 1. Executive Overview

**LatheCAM** is a desktop CAD/CAM application for CNC turning, engineered with a modern, dockable interface inspired by SolidWorks and Fusion 360. It enables machinists and engineers to import 3D CAD models (STEP) and 2D profiles (DXF), visualize and verify geometry in an interactive 3D/2D viewport, generate collision-free turning toolpaths using `LibLathe`, and export production-ready G-code tailored for CNC lathes.

---

## 2. Core Technology Stack

| Layer | Technology | Justification |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.11+ | Orchestrates native C/C++ geometric backends without performance degradation. |
| **Desktop UI / Docking** | **PySide6 (Qt6)** | Industry-standard CAD GUI toolkit; supports native tabbed and floating `QDockWidget` layouts and hierarchical `QTreeView` models. |
| **Theme & UI Polish** | `pyqtdarktheme` | Provides a dark slate aesthetic matching modern engineering workbenches. |
| **B-Rep & STEP Engine** | **OpenCASCADE (`pythonocc-core` / `OCP`)** | Native C++ boundary-representation kernel required to parse STEP files and compute meridian cross-sections ($X-Z$ plane). |
| **2D CAD Ingestion** | **`ezdxf`** | Fast C-accelerated parsing of AutoCAD DXF files (splines, arcs, bulges, polylines). |
| **2D Geometry & Offsets** | **`pyclipper` & `shapely`** | Fast polygon clipping, step-down parallel offsetting, and tool clearance verification. |
| **Lathe CAM Kernel** | **`LibLathe`** | Dedicated turning engine for step-down roughing, facing, finishing, and tool nose radius compensation (TNRC). |
| **3D Rendering Viewport** | **OpenCASCADE AIS** or **`PyVista` (VTK)** | Hardware-accelerated OpenGL rendering of 3D solids, revolved stock cylinders, and interactive toolpath wireframes. |
| **G-Code Post Engine** | Custom Python Post-Processor | Formats coordinate axes, G18 plane geometry, Constant Surface Speed (G96/D), and canned cycles (G71, G76). |

---

## 3. High-Level Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PySide6 (Qt6) Application                       │
│ ┌──────────────────┬─────────────────────────────────┬───────────────┐ │
│ │  Operations Dock │      3D Viewport (Canvas)       │ Property Dock │ │
│ │  - Feature Tree  │  - OpenCASCADE AIS / PyVista    │ - Operation   │ │
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
│ - Shapely Tool Clearance Shadowing    │ │ - Toolpost orientation (1-9) │
└───────────────────┬───────────────────┘ └──────────────┬───────────────┘
                    │                                    │
                    └─────────────────┬──────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Hybrid CAM Solver (LibLathe + Custom)               │
│  - Facing & Longitudinal Roughing passes (LibLathe step-down)          │
│  - Profile finishing with tool nose compensation (LibLathe)            │
│  - Threading (G76 / G33), Peck Parting, and Axial Drilling (G83)       │
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
[ CAD Importer ] ───> Extracts 2D polyline profile on the X-Z plane
         │
         ▼
[ Shapely Shadow ] ─> Filters profile by tool lead/clearance angles to prevent gouging
         │
         ▼
[ Part Model ] ─────> Defines Stock Diameter, Stock Length, and Work Offset (G54)
         │
         ▼
[ Operation Pipeline ]
   ├── Op 1: Face (Stock Z+ to Z0)
   ├── Op 2: OD Roughing (Stepped cuts to shadowed profile + finish allowance)
   ├── Op 3: OD Finishing (Continuous profile tracking)
   ├── Op 4: Threading (G76 cycle + unrolled G33 preview)
   └── Op 5: Peck Part-off / Chamfer
         │
         ▼
[ CAM Engine ] ─────> Solves cutting vectors, retracts, and clearance moves
         │
         ├──> [ 3D Viewport ]: Renders animated tool motion and material removal
         │
         └──> [ Post-Processor ]: Emits final formatted LinuxCNC .ngc file
```

---

## 5. Repository Directory Layout

```text
lathe-cam/
├── ARCHITECTURE.md              # System design and specifications (this file)
├── ANTIGRAVITY_INSTRUCTIONS.md  # Agent rules, guardrails, and milestones
├── pyproject.toml               # Project config and dependencies
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
│       │   ├── shadowing.py     # Shapely tool clearance undercut protection
│       │   └── geometry.py      # Polyline, arc, and 2D vector utilities
│       │
│       ├── cam/                 # Toolpath Generation
│       │   ├── __init__.py
│       │   ├── engine.py        # LibLathe wrapper & bridge
│       │   ├── tools.py         # Lathe tool definitions (CNMG, WNMG, DNMG, parting)
│       │   ├── operations.py    # Threading, Peck Parting, Axial Drilling objects
│       │   └── simulator.py     # Material removal simulation math
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
│       │       └── occ_viewport.py   # OpenCASCADE AIS / PyVista 3D canvas
│       │
│       └── models/              # Application Data Models
│           ├── project.py       # Serialized LatheCAM project state (.lcam)
│           └── stock.py         # Stock cylinder dimensions and offsets
│
└── tests/
    ├── test_step_slicing.py     # Validation of STEP cross-section extraction
    ├── test_dxf_import.py       # Validation of DXF arc/polyline parsing
    ├── test_shadowing.py        # Validation of Shapely undercut clearance clipping
    └── test_post_processor.py   # LinuxCNC G-code syntax and arc offset tests
```

---

## 6. Key Subsystem Implementation Contracts

### 6.1 STEP Cross-Sectioning Contract (`step_importer.py`)
```python
class StepProfileExtractor:
    def __init__(self, step_file_path: str): ...
    
    def extract_xz_profile(self, tolerance: float = 0.001) -> list[tuple[float, float]]:
        """
        Intersects the 3D solid with the X-Z meridian plane (Y=0) using OpenCASCADE's
        BRepAlgoAPI_Section.
        
        Returns:
            List of (X_radius, Z) coordinates representing the upper turning silhouette (X >= 0).
        """
        ...
```

### 6.2 Tool Geometry Definition Contract (`tools.py`)
```python
from dataclasses import dataclass
from enum import Enum

class ToolOrientation(Enum):
    QUADRANT_1 = 1
    QUADRANT_2 = 2
    QUADRANT_3 = 3  # Standard OD right-hand turning
    QUADRANT_4 = 4
    QUADRANT_5 = 5
    QUADRANT_6 = 6
    QUADRANT_7 = 7
    QUADRANT_8 = 8
    QUADRANT_9 = 9

@dataclass
class LatheTool:
    tool_id: int
    name: str
    insert_shape: str          # e.g., 'C' (80 deg), 'D' (55 deg), 'V' (35 deg), 'W'
    nose_radius_mm: float      # e.g., 0.4, 0.8
    clearance_angle_deg: float # Trailing clearance angle
    lead_angle_deg: float      # Approach / lead angle (e.g., 95.0)
    orientation: ToolOrientation
    max_doc_mm: float          # Max depth of cut
```

### 6.3 Post-Processor Output Standards (`linuxcnc.py`)
- **Plane:** Mandatory `G18` (ZX-plane selection).
- **Coordinate Mode:** Default to `G7` (**Diameter Mode** where `X` = diameter, while arc center offsets `I` and `K` remain radius values).
- **Feed Mode:** Default to `G95` (feed per revolution: mm/rev).
- **Speed Mode:** Default to `G96 D{max_rpm} S{css_m_min}` (Constant Surface Speed) for turning and `G97 S{rpm}` for drilling and threading.