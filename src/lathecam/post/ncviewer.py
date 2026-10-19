from __future__ import annotations

import math
from typing import Any, Sequence

from lathecam.cad.geometry import _project_center_to_bisector
from lathecam.cam.commands import MotionCmd
from lathecam.post.base_post import BasePostProcessor


class NCViewerPostProcessor(BasePostProcessor):
    """Post-processor generating Universal ISO / NC Viewer compatible lathe G-code (.nc).
    
    Designed specifically for WebGL / Cartesian G-code backplotters (NC Viewer, CAMotics):
    - Dedicated `G18` line so single-G-per-line parsers reliably enter XZ lathe plane mode.
    - Consistent 1:1 Radial coordinates (G8 / Radius Mode) so `center_x = start_x + I` has
      identical start/end radii (`r_start == r_end`) without requiring hidden viewer toggles.
    - XZ plane arc chirality (`G02` / `G03`) matched to Three.js / WebGL `atan2(dZ, dX)` convention.
    - Automatic unrolling of `G76` threading and `G83` peck drilling canned cycles into explicit
      `G00` / `G01` passes so external visualizers display all threading and drilling moves.
    """

    def __init__(self, is_diameter_mode: bool = False, xz_arc_chirality: bool = True) -> None:
        super().__init__(is_diameter_mode=is_diameter_mode)
        self.xz_arc_chirality = xz_arc_chirality

    def _fmt(self, val: float) -> str:
        return f"{val:.3f}"

    def export(
        self,
        commands: Sequence[MotionCmd],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        lines: list[str] = []

        comment_hdr = meta.get("program_name", "LATHECAM - UNIVERSAL NCVIEWER SIMULATOR")
        lines.append(f"({comment_hdr.upper()})")
        lines.append("(COORDINATE MODE: 1:1 RADIUS MODE FOR CARTESIAN BACKPLOTTERS)")
        lines.append("G21 G40 G80 G90")
        lines.append("G18")

        x_scale = 2.0 if self.is_diameter_mode else 1.0
        curr_x_rad: float | None = None
        curr_z: float | None = None
        last_mode: str | None = None

        for cmd in commands:
            if cmd.mode == "COMMENT":
                text = cmd.raw_params.get("comment", "") if cmd.raw_params else ""
                lines.append(f"({text.upper()})")
                continue

            if cmd.mode == "TOOL_CHANGE":
                t_id = int(cmd.raw_params.get("tool_id", 1)) if cmd.raw_params else 1
                lines.append(f"M06 T{t_id:02d}")
                last_mode = None
                continue

            if cmd.mode == "SPINDLE_CSS":
                params = cmd.raw_params or {}
                s_css = int(params.get("css_m_min", 200))
                lines.append(f"S{s_css * 5} M03")
                continue

            if cmd.mode == "SPINDLE_RPM":
                params = cmd.raw_params or {}
                s_rpm = int(params.get("rpm", 1000))
                lines.append(f"S{s_rpm} M03")
                continue

            if cmd.mode in ("G0", "G1", "G33"):
                eff_mode = "G1" if cmd.mode == "G33" else cmd.mode
                next_x_rad = round(cmd.x * x_scale, 3) / x_scale if cmd.x is not None else curr_x_rad
                next_z = round(cmd.z, 3) if cmd.z is not None else curr_z
                if (
                    eff_mode == "G0"
                    and last_mode == "G0"
                    and curr_x_rad is not None
                    and curr_z is not None
                    and next_x_rad is not None
                    and next_z is not None
                    and abs(next_x_rad - curr_x_rad) < 1e-6
                    and abs(next_z - curr_z) < 1e-6
                ):
                    continue

                code = "G00" if eff_mode == "G0" else "G01"
                parts = [code]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                feed = cmd.f if cmd.f is not None else (cmd.k if cmd.mode == "G33" else None)
                if feed is not None and eff_mode == "G1":
                    parts.append(f"F{self._fmt(feed)}")
                lines.append(" ".join(parts))
                curr_x_rad = next_x_rad
                curr_z = next_z
                last_mode = eff_mode
                continue

            if cmd.mode in ("G2", "G3"):
                next_x_rad = round(cmd.x * x_scale, 3) / x_scale if cmd.x is not None else curr_x_rad
                next_z = round(cmd.z, 3) if cmd.z is not None else curr_z
                i_val = cmd.i
                k_val = cmd.k
                if (
                    curr_x_rad is not None
                    and curr_z is not None
                    and next_x_rad is not None
                    and next_z is not None
                    and i_val is not None
                    and k_val is not None
                ):
                    raw_c = (curr_z + k_val, curr_x_rad + i_val)
                    raw_r = math.hypot(k_val, i_val)
                    exact_c, _ = _project_center_to_bisector((curr_z, curr_x_rad), (next_z, next_x_rad), raw_c, raw_r)
                    k_val = exact_c[0] - curr_z
                    i_val = exact_c[1] - curr_x_rad

                if self.xz_arc_chirality:
                    code = "G03" if cmd.mode == "G2" else "G02"
                else:
                    code = "G02" if cmd.mode == "G2" else "G03"

                parts = [code]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                if i_val is not None:
                    parts.append(f"I{self._fmt(i_val * x_scale)}")
                if k_val is not None:
                    parts.append(f"K{self._fmt(k_val)}")
                if cmd.f is not None:
                    parts.append(f"F{self._fmt(cmd.f)}")
                lines.append(" ".join(parts))
                curr_x_rad = next_x_rad
                curr_z = next_z
                last_mode = cmd.mode
                continue

            if cmd.mode in ("G41", "G42", "G40"):
                parts = ["G01"]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                    curr_x_rad = round(cmd.x * x_scale, 3) / x_scale
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                    curr_z = round(cmd.z, 3)
                if cmd.f is not None:
                    parts.append(f"F{self._fmt(cmd.f)}")
                lines.append(" ".join(parts))
                last_mode = "G1"
                continue

        lines.append("M05")
        lines.append("M09")
        lines.append("M30")
        return "\n".join(lines) + "\n"
