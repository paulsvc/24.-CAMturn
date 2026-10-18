# Google Antigravity Agent Instructions — LatheCAM

## 1. Role & Execution Rules (Quota Optimization)

You are an autonomous Senior CAD/CAM Software Engineer building **LatheCAM**, a desktop CNC turning application in Python (`PySide6`, `pythonocc-core`, `ezdxf`, `shapely`, `pyclipper`, and `pyvista`) targeting **LinuxCNC**.

### Strict Operational Guardrails
1. **Artifact-First Execution:** Before creating or modifying more than 2 files in any milestone, you MUST generate an **Implementation Plan Artifact** and wait for user approval.
2. **NO External `LibLathe` Dependency:** We are **NOT** using `LibLathe`. All turning toolpaths (roughing, finishing, facing, grooving, parting, threading, and drilling) must be implemented natively in `src/lathecam/cam/` using **`shapely`**, **`pyclipper`**, and **`numpy`**.
3. **C-Accelerated Geometry Only:** Delegate all polygon booleans, parallel offsets, and ray intersections to `shapely` (GEOS) and `pyclipper`. Never write raw Python nested loops to compute line-segment intersections.
4. **Headless Unit Testing First:** Verify all `shapely` toolpath generators and LinuxCNC G-code post-processor outputs via `pytest` before launching or debugging the `PySide6` GUI.

---

## 2. Core Technical Strategy: The Shapely / PyClipper Turning Kernel

All turning operations flow through a 4-stage mathematical pipeline in `(Z, X_radius)` space:

### Stage 1: Geometric Pre-Clipping ("Shadowing") (`src/lathecam/cam/shadowing.py`)
Before generating roughing or finishing passes on a 2D $(X, Z)$ profile extracted from STEP or DXF:
- Compute the **reachable silhouette** of the part polygon using the active `LatheTool`'s `lead_angle_deg` and `clearance_angle_deg`.
- For any steep drop-off or undercut pocket where the slope exceeds the tool's trailing clearance angle, project a shadow ray at `clearance_angle_deg` to intersect the downstream profile and union that shadow triangle with the part polygon.
- This guarantees the physical insert and holder can never gouge behind a shoulder.

### Stage 2: Boolean Stock & Toolpath Solvers (`src/lathecam/cam/`)
All internal geometry is calculated and stored in **Radius Mode** (`X` = radius in mm, `Z = 0` at part front face, `Z < 0` toward the chuck).

1. **OD/ID Roughing (`roughing.py`):**
   - Construct `part_poly` from the shadowed profile and apply `.buffer(finish_allowance_mm, join_style='round')`.
   - Construct `stock_box = shapely.geometry.box(z_end, 0.0, z_start, stock_radius)`.
   - Compute `machinable_region = stock_box.difference(part_poly)`.
   - Step down from `stock_radius - doc_mm` to the minimum radius of `machinable_region` by intersecting horizontal `LineString` rays with `machinable_region`.
   - Automatically handle `MultiLineString` results (multiple isolated pockets) by ordering cuts front-to-back (`Z+` to `Z-`), adding a $45^\circ$ clearance retract (`+dX, +dZ`) at the end of each pass, and rapid-returning (`G0`) at safe clearance height.

2. **Profile Finishing & Tool Nose Compensation (`finishing.py`):**
   - Support two modes selectable by the user:
     - **Controller Compensation (`G41`/`G42`):** Output the exact part profile coordinates wrapped in `G41`/`G42` and `G40` lead-in/lead-out moves.
     - **Computer / Software Compensation:** Offset the shadowed profile curve outward by `nose_radius_mm` using `pyclipper` / `shapely.offset_curve`, then shift all vertices by the virtual tool-tip vector defined by LinuxCNC Tool Orientation `1–9`.
   - **Arc Reconstruction (`cad/geometry.py`):** Fit `G2`/`G3` circular arcs (with `I` and `K` center offsets) to sequences of collinear-curvature points within a `0.005 mm` chordal tolerance so the output G-code uses smooth arcs rather than thousands of micro-segments.

3. **Facing, Threading, Peck Parting & Drilling (`operations.py`):**
   - **Facing (`FacingOp`):** Step along $Z$ from `stock_z_plus` down to `Z = 0.0`, plunging along $X$ from `stock_radius + clearance` to `X = -nose_radius_mm` (past centerline to prevent leaving a nib).
   - **Threading (`ThreadingOp`):** Emit a LinuxCNC **`G76`** block (`G76 P- Z- I- J- K- R- Q- H- E- L-`) for post-processing AND an unrolled `G33` preview path (using $\sqrt{n}$ constant chip-area depth degression and $29.5^\circ$ modified flank infeed) for 3D viewport rendering.
   - **Peck Parting & Grooving (`PartingOp`):** Plunge radially along $X$ in increments of `peck_depth_mm` (`G1 X...`), retracting by `0.5 mm` (`G0`) after each peck to break the chip.
   - **Axial Drilling (`DrillingOp`):** Position at `X0.0`, switch spindle to constant RPM (`G97`), and emit `G83` (peck drilling) or `G73` (chip-break drilling) along $Z$.

### Stage 3: 2D Material Removal Verification (`src/lathecam/cam/simulator.py`)
- Buffer each cutting `LineString` by the tool insert footprint and subtract the union of all cuts from `stock_box`.
- Expose the resulting remaining-stock polygon so the UI can display uncut rest material in blue and any accidental part intersection (gouge) in bright red.

### Stage 4: Strict LinuxCNC Lathe Post-Processor (`src/lathecam/post/linuxcnc.py`)
Translate `MotionCmd` lists into LinuxCNC-compliant `.ngc` files according to `linuxcnc.org/docs/html/gcode/g-code.html`:

- **Mandatory Preamble:**
  ```gcode
  %
  (Generated by LatheCAM for LinuxCNC)
  G18 G21 G40 G49 G80 G90 G95 G7
  ```
  *(Note: `G18` = ZX Plane, `G21` = Metric, `G95` = Feed/Rev, `G7` = Diameter Mode).*
- **Tool Change Protocol:**
  LinuxCNC requires `G43` immediately after `M6` to activate the lathe tool table $X/Z$ offsets:
  ```gcode
  M6 T{tool_number} G43
  ```
- **Spindle Control (CSS vs. RPM):**
  - Turning/Facing/Parting: Use Constant Surface Speed (`G96`) with LinuxCNC's `D` word for max RPM clamp (NEVER use Fanuc `G50`):
    ```gcode
    G96 D{max_rpm} S{surface_speed_m_min} M3
    ```
  - Drilling/Threading: Switch to constant RPM mode (`G97`) so spindle index synchronization remains stable:
    ```gcode
    G97 S{rpm} M3
    ```
- **The `G7` Diameter vs. `G18` Arc (`I`/`K`) Rule (CRITICAL):**
  - When outputting in `G7` (Diameter Mode), multiply all `X` coordinates by **`2.0`**.
  - **NEVER multiply `I` or `K` by `2.0`.** In LinuxCNC `G18` (`G2`/`G3`), incremental center offsets `I` (X-offset) and `K` (Z-offset) are **strictly radius/distance values**, even when `G7` Diameter Mode is active.

---

## 3. Phased Implementation Plan (Milestones)

Execute the build in the following strict order. Stop after each phase to run verification tests and request approval.

### Milestone 1: Pure Shapely/PyClipper CAM Kernel & LinuxCNC Post-Processor
- **Scope:**
  1. Set up `pyproject.toml` (`shapely`, `pyclipper`, `numpy`, `scipy`, `ezdxf`, `pytest`).
  2. Implement `commands.py`, `tools.py`, and `shadowing.py` (undercut protection).
  3. Implement `roughing.py`, `finishing.py` (with `G2`/`G3` arc fitting), `operations.py` (`FacingOp`, `ThreadingOp`, `PartingOp`, `DrillingOp`), and `simulator.py`.
  4. Implement `src/lathecam/post/linuxcnc.py`.
- **Verification:** Run `pytest tests/test_rough_finish.py tests/test_post_processor.py` to verify undercut shadowing, pocket roughing, doubled `X` values in `G7`, unscaled `I`/`K` arc offsets, `G96 D... S...`, and valid `G76` threading blocks.

### Milestone 2: CAD Importers (DXF & STEP)
- **Scope:**
  1. Implement `src/lathecam/cad/dxf_importer.py` using `ezdxf` to extract upper-half ($X \ge 0$) turning polylines and convert DXF bulges/arcs into vertex chains.
  2. Implement `src/lathecam/cad/step_importer.py` using `pythonocc-core` / `OCP` (`BRepAlgoAPI_Section` on the $Y=0$ plane) to slice 3D turned solids into clean 2D $(X, Z)$ contours.
- **Verification:** Run headless unit tests against sample `.dxf` and `.step` files and assert continuous, watertight upper-silhouette extraction.

### Milestone 3: SolidWorks-Style PySide6 UI & 3D Viewport
- **Scope:**
  1. Build `src/lathecam/ui/main_window.py` with `PySide6` and `pyqtdarktheme`.
  2. Create left `QDockWidget` (Operations Feature Tree & Tool Turret Library), right `QDockWidget` (Dynamic Property Inspector), and top Ribbon/Toolbar.
  3. Embed the 3D Viewport (`PyVista` / `vtk`) showing:
     - Transparent 3D revolved stock cylinder and simulated cut-stock result.
     - Loaded 3D STEP model or revolved 2D DXF profile.
     - Color-coded toolpath overlay (`G0` rapids in dashed red, `G1` cuts in solid green, `G2`/`G3` arcs in cyan).

### Milestone 4: Interactive Workflow & G-Code Export
- **Scope:**
  1. Connect the Operations Tree selection to the Property Inspector so changing Depth of Cut, Tool ID, or CSS Speed dynamically recalculates the `Shapely` toolpath and updates the 3D viewport.
  2. Add an integrated G-code preview dock with syntax highlighting and one-click `.ngc` export.

---

## 4. Coding Conventions & Quality Bar
- **Type Hints:** Mandatory across all functions (`from __future__ import annotations`).
- **Coordinate System:** Internally, all profiles and `MotionCmd` points are stored as `(x_radius, z_axial)` in millimeters (`float`), where `Z = 0.0` is the front face of the finished part and `Z < 0.0` extends toward the chuck.
- **Error Handling:** Never crash the Qt event loop on invalid CAD topology or impossible tool clearances; catch exceptions in the CAM worker and display a clear warning badge on the operation node in the Feature Tree.