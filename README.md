# LatheCAM — CNC Turning CAD/CAM Workbench for LinuxCNC

[![English Version](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Version Française](https://img.shields.io/badge/Langue-Français-green.svg)](README_fr.md)

**LatheCAM** is a professional open-source desktop CAD/CAM application for CNC turning built with **PySide6 (Qt6)**, **PyVista (VTK)**, **OpenCASCADE (`cadquery-ocp`)**, **`ezdxf`**, **`Shapely` (GEOS)**, and **`PyClipper`**.

---

## UI Screenshots & Interactive Workflow Showcase

### 1. Animated Tool Simulation Playback with 3D Insert & Shank (GIF)
![Toolpath Playback Simulation](docs/images/simulation_playback.gif)

### 2. Tool Turret & ISO Insert Library Editor (Live 2D Blueprint Preview)
![Tool Library Editor](docs/images/screenshot_8_tool_library_editor.png)

### 3. Interactive 3D CAD Face Selection & Operation Assignment Bar
![3D Interactive CAD Face Selection](docs/images/screenshot_6_face_selection_3d.png)

### 4. Interactive Kinematic Toolpath Playback in 3D Viewport
![Toolpath Kinematic Simulation](docs/images/screenshot_9_tool_simulation_viewer.png)

### 5. Face-Bounded 2D ZX Roughing (`F7: Cylinder Ø25.0 × 10.0mm`)
![Face-Bounded 2D Roughing](docs/images/screenshot_7_face_bounded_roughing_2d.png)

### 6. Animated End-to-End Workflow & Cut Simulation (GIF)
![LatheCAM Interactive Face Selection, Toolpath Generation & 3D Material Removal Simulation](docs/images/lathecam_workflow_simulation.gif)

### 7. 3D Workbench Overview (Dark Theme — English)
![3D Isometric Workbench Overview](docs/images/screenshot_1_3d_overview.png)

### 8. White / Light CAD Theme & French Translation (Français)
![White CAD Theme and French Translation](docs/images/screenshot_5_white_theme_french.png)

### 9. 2D ZX Lathe Plane Roughing & Retracts
![2D ZX Roughing Passes](docs/images/screenshot_2_roughing_2d_zx.png)

### 10. 2D ZX Lathe Plane Profile Finishing with TNRC & Fitted G2/G3 Arcs
![2D ZX Profile Finishing](docs/images/screenshot_3_finishing_tnrc_arcs.png)

### 11. 3D Material Removal & Threading Simulation
![3D Cut Simulation and Threading](docs/images/screenshot_4_3d_cut_simulation.png)

---

## Key Capabilities

### 1. Tool Turret & ISO Insert Library Editor (`src/lathecam/cam/tools.py` & `src/lathecam/ui/dialogs/`)
- **Full ISO Standard Insert Geometries:**
  - **C**: $80^\circ$ Rhombic / Diamond (CNMG, CCMT)
  - **D**: $55^\circ$ Rhombic / Diamond (DNMG, DCMT)
  - **V**: $35^\circ$ Rhombic / Diamond (VNMG, VBMT)
  - **W**: $80^\circ$ Trigon (WNMG)
  - **T**: $60^\circ$ Triangular (TNMG, TCMT)
  - **S**: $90^\circ$ Square (SNMG, SCMT)
  - **R**: Round / Circular (RNMG, RCMT)
  - **K**: $55^\circ$ Parallelogram (KNUX)
  - **PART**: Parting & Grooving blade
  - **THREAD**: $60^\circ$ External / Internal threading insert
  - **DRILL**: Axial twist & center drill
- **Live 2D Blueprint Preview:** Antialiased vector preview rendering exact polygon silhouettes, nose radius $r_\epsilon$ corner filleting, dashed inscribed circle ($IC$), center mounting hole, and live dimension callouts.
- **Parametric Dimension Controls:** Inscribed Circle ($IC$), Thickness ($s$), Corner Nose Radius ($r_\epsilon$), Edge Length ($l$), Tip Cut Width ($w$), Lead / Approach Angle ($\kappa_r$), Flank Clearance Angle ($\alpha$), Max DOC ($a_p$), Hand (R/L/N), and LinuxCNC Tool Orientation (Q1–Q9).
- **16 Built-in Industry Presets:** Quick 1-click presets for CNMG 120408, DNMG 150604, VNMG 160404, WNMG 080408, TNMG 160408, SNMG 120408, RCMT 1204MO, KNUX 160405R, Parting blades, Threading 16ER, and Drills.
- **Turret Pocket Management:** Add, Duplicate, Delete, Reset to Factory Defaults, and JSON Library Import / Export.
- **Project Persistence:** Tools and custom dimensions are serialized into `.lcam` project files and automatically update parametric 3D VTK meshes.

### 2. Interactive Tool Simulation & Trajectory Playback (`src/lathecam/ui/docks/simulation_dock.py` & `src/lathecam/cam/tool_mesh.py`)
- **3D Tool Following Path:** The complete parametric 3D tool (insert with nose radius + steel shank holder) moves smoothly along generated toolpaths in real time.
- **Transport Controls:** Play, Pause, Stop, Step Forward, Step Backward, and Scrubbing Slider.
- **Speed Multiplier:** Adjustable playback speed from $0.1\times$ to $10.0\times$.
- **Real-Time Kinematic Readout:** Live display of coordinates ($Z$, $X$ radius, $X$ diameter), current Feedrate ($F$), current Operation name, and Motion Type (Rapid / Cut / Retract).
- **Dynamic Cut Trail:** Color-coded trail showing feed cuts in green, rapid moves in cyan/red, and retract moves in yellow.

### 3. CAD Ingestion (`src/lathecam/cad/`)
- **3D B-Rep STEP Importer (`step_importer.py`):**
  - Slices 3D STEP/STP turned solids on the meridian $Y = 0$ ($X-Z$) plane via OpenCASCADE `BRepAlgoAPI_Section`.
  - Full support for hollow cylinders, bored shafts, and internal profiles.
  - Automatically cleans up existing operations and resets selections upon importing new files.
  - Adaptively discretizes curves within `0.005 mm` chordal deflection tolerance.
- **2D AutoCAD DXF Importer (`dxf_importer.py`):** Parses `LWPOLYLINE` (including circular arc bulges), `LINE`, `ARC`, and `SPLINE` entities, topologically chaining unordered segments into watertight upper-half ($X \ge 0$) profiles.
- **Least-Squares Circular Arc Fitter (`geometry.py`):** Reconstructs `G2`/`G3` circular arcs with incremental `(I, K)` centers from discretized offset polylines within `0.005 mm` tolerance.

### 4. Pure Shapely / PyClipper Turning Kernel (`src/lathecam/cam/`)
- **Undercut Shadowing (`shadowing.py`):** Projects tool trailing-flank clearance rays and lead-angle wedges to bridge unreachable undercuts and prevent shoulder gouging.
- **Boolean Roughing (`roughing.py`):** Computes `Stock_Box - Buffered_Part`, slices horizontal $Z$-rays, orders multi-pocket `MultiLineString` passes front-to-back, and appends $45^\circ$ clearance retracts.
- **Profile Finishing (`finishing.py`):**
  - Supports both **Controller Compensation (`G41`/`G42`)** and **Computer Tool Nose Radius Compensation (PyClipper parallel offset + LinuxCNC Orientation `1–9` virtual tool-tip shift)**.
  - Robust handling of vertical shoulder faces, fillets, chamfers, and tapers without degenerate polygon exceptions.
- **Parametric Operations (`operations.py`):**
  - `FacingOp`: Steps along $Z$ and plunges past centerline to $-R_{\text{nose}}$ to eliminate center nibs.
  - `ThreadingOp`: Emits canonical LinuxCNC `G76` cycle blocks and unrolled `G33` constant-chip-area ($\sqrt{n}$) preview passes with $29.5^\circ$ modified flank infeed.
  - `PartingOp`: Radial pecking with $0.5\text{ mm}$ chip-break retracts.
  - `DrillingOp`: Axial centerline `G83`/`G73` peck drilling with constant RPM (`G97`).
- **2D Material Removal Verification (`simulator.py`):** Swept-tool boolean subtraction computing remaining stock, uncut rest material, and collision/gouge verification.

### 5. Strict LinuxCNC & Fanuc Post-Processors (`src/lathecam/post/`)
- **LinuxCNC Post-Processor (`linuxcnc.py`):**
  - Emits `G18 G21 G40 G49 G80 G90 G95 G7` preamble.
  - Formats clean comments preventing nested comment syntax errors in LinuxCNC.
  - Enforces 2-axis lathe compatibility (no invalid G18 canned cycle plane conflicts on machines without Y-axis).
  - Enforces `T{id} M6 G43` tool change protocol and `G96 D{max_rpm} S{css} M3` constant surface speed clamp.
  - Formats `X` coordinates in `G7` Diameter Mode while keeping `G18` arc center offsets `I` and `K` strictly unscaled radial distances.
- **Fanuc 0i-TF / ISO Post-Processor (`fanuc.py`):**
  - Emits `G50 S{max_rpm}` spindle clamp, `T0101` offset calls, and 2-block `G76` threading cycles.

### 6. SolidWorks / Fusion-Style PySide6 Desktop Workbench (`src/lathecam/ui/`)
- Dockable `FeatureManager` operations tree, `ToolTurretLibrary`, dynamic `PropertyInspector`, syntax-highlighted `LinuxCNC G-Code Output` dock, and interactive 3D/2D `PyVista` VTK viewport.
- Interactive 3D face picking allowing 1-click assignment of face-bounded roughing, finishing, facing, and grooving operations.
- Dark & Light CAD themes with full English and French localization.

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

### Run Automated Unit Tests (44 Tests)
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
