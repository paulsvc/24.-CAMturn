# LatheCAM — CNC Turning CAD/CAM Workbench for LinuxCNC

**LatheCAM** is a desktop CAD/CAM application for CNC turning built with **PySide6 (Qt6)**, **PyVista (VTK)**, **OpenCASCADE (`cadquery-ocp`)**, **`ezdxf`**, **`Shapely` (GEOS)**, and **`PyClipper`**.

---

## UI Screenshots & Interactive Workflow Showcase

### Animated End-to-End Workflow & Cut Simulation (GIF)
![LatheCAM Interactive Face Selection, Toolpath Generation & 3D Material Removal Simulation](docs/images/lathecam_workflow_simulation.gif)

### 1. Interactive 3D CAD Face Selection & Operation Assignment Bar
![3D Interactive CAD Face Selection](docs/images/screenshot_6_face_selection_3d.png)

### 2. Face-Bounded 2D ZX Roughing (`F7: Cylinder Ø25.0 × 10.0mm`)
![Face-Bounded 2D Roughing](docs/images/screenshot_7_face_bounded_roughing_2d.png)

### 3. 3D Workbench Overview (Dark Theme — English)
![3D Isometric Workbench Overview](docs/images/screenshot_1_3d_overview.png)

### 4. White / Light CAD Theme & French Translation (Français)
![White CAD Theme and French Translation](docs/images/screenshot_5_white_theme_french.png)

### 5. 2D ZX Lathe Plane Roughing & Retracts
![2D ZX Roughing Passes](docs/images/screenshot_2_roughing_2d_zx.png)

### 6. 2D ZX Lathe Plane Profile Finishing with TNRC & Fitted G2/G3 Arcs
![2D ZX Profile Finishing](docs/images/screenshot_3_finishing_tnrc_arcs.png)

### 7. 3D Material Removal & Threading Simulation
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

**Option 1 — Simple (All platforms: PowerShell, CMD, Linux, macOS):**
```powershell
python run.py
```

**Option 2 — Windows PowerShell script:**
```powershell
.\run.ps1
```

**Option 3 — Windows Command Prompt / Double-click:**
```cmd
run.bat
```

**Option 4 — Module with environment variable:**
- **PowerShell:**
  ```powershell
  $env:PYTHONPATH = "src"; python -m lathecam.main
  ```
- **Linux / macOS / Git Bash:**
  ```bash
  PYTHONPATH=src python -m lathecam.main
  ```

### Run Headless Unit Tests
```bash
python -m pytest -v
```

---

## Sample CNC G-Code Outputs & Automated Verification

All generated G-code programs are automatically checked by the built-in **G-Code Geometric Verifier & Backplotter (`src/lathecam/post/verifier.py`)** (verifying sub-micron arc center consistency $|R_{\text{start}} - R_{\text{end}}| \le 0.0004\text{ mm}$, orthogonal rapid clearances, and zero part gouging) and published in the [`gcode/`](gcode/) folder:

- **[`gcode/stepped_shaft_ncviewer.nc`](gcode/stepped_shaft_ncviewer.nc)** *(Recommended for [ncviewer.com](https://ncviewer.com) & CAMotics)*: 1:1 Radial coordinates (`r_start == r_end`), dedicated `G18` XZ plane arc chirality, and unrolled multi-pass threading & peck drilling.
- **[`gcode/stepped_shaft_linuxcnc.ngc`](gcode/stepped_shaft_linuxcnc.ngc)**: LinuxCNC / Machinekit lathe dialect with `G7` diameter mode, `T<id> M6 G43`, `G96 D<rpm> S<css>`, `G2`/`G3` TNRC finishing, `G76` threading, and `G83` drilling.
- **[`gcode/stepped_shaft_fanuc.nc`](gcode/stepped_shaft_fanuc.nc)**: Fanuc 0i-TF / ISO dialect with `G50 S<rpm>`, `T0101`, `G96 S<css> M03`, 2-block `G76` threading cycle, and `G28` reference return.
- **[`gcode/stepped_shaft_face_bounded.ngc`](gcode/stepped_shaft_face_bounded.ngc)**: Example demonstrating interactive CAD face-bounded selective roughing.



