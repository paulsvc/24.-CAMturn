# LatheCAM — CNC Turning CAD/CAM Workbench for LinuxCNC

**LatheCAM** is a desktop CAD/CAM application for CNC turning built with **PySide6 (Qt6)**, **PyVista (VTK)**, **OpenCASCADE (`cadquery-ocp`)**, **`ezdxf`**, **`Shapely` (GEOS)**, and **`PyClipper`**.

---

## UI Screenshots & Showcase

### 1. 3D Workbench Overview (Dark Theme — English)
![3D Isometric Workbench Overview](docs/images/screenshot_1_3d_overview.png)

### 2. White / Light CAD Theme & French Translation (Français)
![White CAD Theme and French Translation](docs/images/screenshot_5_white_theme_french.png)

### 3. 2D ZX Lathe Plane Roughing & Retracts
![2D ZX Roughing Passes](docs/images/screenshot_2_roughing_2d_zx.png)

### 4. 2D ZX Lathe Plane Profile Finishing with TNRC & Fitted G2/G3 Arcs
![2D ZX Profile Finishing](docs/images/screenshot_3_finishing_tnrc_arcs.png)

### 5. 3D Material Removal & Threading Simulation
![3D Cut Simulation and Threading](docs/images/screenshot_4_3d_cut_simulation.png)

---

## Key Capabilities

1. **CAD Ingestion (`src/lathecam/cad/`):**
   - **3D B-Rep STEP Importer (`step_importer.py`):** Slices 3D STEP/STP turned solids on the meridian $Y = 0$ ($X-Z$) plane via OpenCASCADE `BRepAlgoAPI_Section` and adaptively discretizes curves within `0.005 mm` deflection tolerance.
   - **2D AutoCAD DXF Importer (`dxf_importer.py`):** Parses `LWPOLYLINE` (including circular arc bulges), `LINE`, `ARC`, and `SPLINE` entities, topologically chaining unordered segments into watertight upper-half ($X \ge 0$) profiles.
   - **Least-Squares Circular Arc Fitter (`geometry.py`):** Reconstructs `G2`/`G3` circular arcs with incremental `(I, K)` centers from discretized offset polylines within `0.005 mm` chordal tolerance.

2. **Pure Shapely / PyClipper Turning Kernel (`src/lathecam/cam/`):**
   - **Undercut Shadowing (`shadowing.py`):** Projects tool trailing-flank clearance rays and lead-angle wedges to bridge unreachable undercuts and prevent shoulder gouging.
   - **Boolean Roughing (`roughing.py`):** Computes `Stock_Box - Buffered_Part`, slices horizontal $Z$-rays, orders multi-pocket `MultiLineString` passes front-to-back, and appends $45^\circ$ clearance retracts.
   - **Profile Finishing (`finishing.py`):** Supports both **Controller Compensation (`G41`/`G42`)** and **Computer Tool Nose Radius Compensation (PyClipper parallel offset + LinuxCNC Orientation `1–9` virtual tool-tip shift)**.
   - **Parametric Operations (`operations.py`):**
     - `FacingOp`: Steps along $Z$ and plunges past centerline to $-R_{\text{nose}}$ to eliminate center nibs.
     - `ThreadingOp`: Emits canonical LinuxCNC `G76` cycle blocks and unrolled `G33` constant-chip-area ($\sqrt{n}$) preview passes with $29.5^\circ$ modified flank infeed.
     - `PartingOp`: Radial pecking with $0.5\text{ mm}$ chip-break retracts.
     - `DrillingOp`: Axial centerline `G83`/`G73` peck drilling with constant RPM (`G97`).
   - **2D Material Removal Verification (`simulator.py`):** Swept-tool boolean subtraction computing remaining stock, uncut rest material, and collision/gouge verification.

3. **Strict LinuxCNC Lathe Post-Processor (`src/lathecam/post/linuxcnc.py`):**
   - Emits `G18 G21 G40 G49 G80 G90 G95 G7` preamble.
   - Enforces `T{id} M6 G43` tool change protocol and `G96 D{max_rpm} S{css} M3` constant surface speed clamp.
   - Doubles `X` coordinates in `G7` Diameter Mode while keeping `G18` arc center offsets `I` and `K` strictly unscaled radius/distance values.

4. **SolidWorks / Fusion-Style PySide6 Desktop Workbench (`src/lathecam/ui/`):**
   - Dockable `FeatureManager` operations tree, `ToolTurretLibrary`, dynamic `PropertyInspector`, syntax-highlighted `LinuxCNC G-Code Output` dock, and interactive 3D/2D `PyVista` VTK viewport.

---

## Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch Desktop Application
```bash
PYTHONPATH=src python -m lathecam.main
```

### Run Headless Unit Tests
```bash
python -m pytest -v
```
